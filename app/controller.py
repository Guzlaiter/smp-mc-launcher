"""
Логика лаунчера без tkinter: проверка/установка обновлений сборки и запуск игры.

С интерфейсом общается только через UiBridge — контроллер не знает ни про окна, ни про цвета.
Тяжёлые операции идут в фоновом потоке; одновременно выполняется только одна
(нельзя нажать PLAY во время обновления).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.config import GITHUB_REPO, TEST_RELEASE_DIR, is_test_mode, save_config
from app.github_updater import GithubUpdater, LocalUpdater, UpdateError
from app.minecraft import (
    MinecraftError,
    build_launch_command,
    install_minecraft,
    install_neoforge,
    installed_version_ids,
    launch_minecraft,
)
from app.utils import human_size, log


@dataclass
class UiBridge:
    """Что контроллеру нужно от интерфейса. Все вызовы приходят в UI-потоке (кроме call)."""
    call: Callable[[Callable[[], None]], None]   # выполнить функцию в UI-потоке
    status: Callable[[str, str], None]           # (текст, уровень: info|ok|warn|error)
    progress: Callable[[int, str], None]         # (процент, текст)
    busy: Callable[[bool], None]                 # идёт ли операция
    confirm: Callable[[str, str], bool]          # диалог да/нет
    quit: Callable[[], None]                     # закрыть лаунчер


class LauncherController:
    def __init__(self, cfg: dict, ui: UiBridge):
        self.cfg = cfg
        self.ui = ui
        self._lock = threading.Lock()

        self.test_mode = is_test_mode()
        if self.test_mode:
            self.updater = LocalUpdater(TEST_RELEASE_DIR)
        else:
            self.updater = GithubUpdater(GITHUB_REPO) if "/" in GITHUB_REPO else None

    # ==================================================================
    #                           Публичное API
    # ==================================================================
    def update_config(self, new_cfg: dict) -> None:
        self.cfg = new_cfg
        save_config(new_cfg)

    def version_label(self) -> str:
        return f"NeoForge | MC {self.cfg.get('minecraft_version', '?')}"

    def check_updates(self) -> None:
        if not self.updater:
            self._status("Источник сборки не настроен", "error")
            return
        self._start(self._check_job)

    def play(self) -> None:
        self._start(self._play_job)

    # ==================================================================
    #                    Запуск задач / общение с UI
    # ==================================================================
    def _start(self, job: Callable[[], None]) -> None:
        if not self._lock.acquire(blocking=False):
            self._status("Дождитесь завершения текущей операции", "warn")
            return
        self._ui(lambda: self.ui.busy(True))
        self._progress(0, "")

        def runner():
            try:
                job()
            except Exception as e:  # страховка: поток не должен умирать молча
                log.exception("job failed")
                self._status(f"Ошибка: {e}", "error")
            finally:
                self._lock.release()
                self._ui(lambda: self.ui.busy(False))

        threading.Thread(target=runner, daemon=True).start()

    def _ui(self, fn: Callable[[], None]) -> None:
        try:
            self.ui.call(fn)
        except Exception:  # окно уже закрыто
            pass

    def _status(self, text: str, level: str = "info") -> None:
        self._ui(lambda: self.ui.status(text, level))

    def _progress(self, pct: int, text: str = "") -> None:
        self._ui(lambda: self.ui.progress(pct, text))

    def _confirm(self, title: str, message: str) -> bool:
        """Диалог из рабочего потока: показываем в UI-потоке и ждём ответ."""
        done, answer = threading.Event(), [False]

        def ask():
            try:
                answer[0] = bool(self.ui.confirm(title, message))
            finally:
                done.set()

        self._ui(ask)
        done.wait()
        return answer[0]

    # ==================================================================
    #                           Обновления
    # ==================================================================
    def _check_job(self) -> None:
        try:
            self._status("Проверка источника...")
            release = None
            if self.test_mode:
                tag = self.updater.get_local_version()
            else:
                release = self.updater.get_latest_release()
                tag = release.get("tag_name", "?")

            if self._read_local_version() == tag:
                self._status(f"Сборка актуальна ({tag})", "ok")
                return

            self._status(f"Доступна версия {tag}", "warn")
            if self._confirm("Обновление",
                             f"Доступна новая версия сборки {tag}.\nОбновить сейчас?"):
                self._update_job(tag, release)
        except UpdateError as e:
            self._status(str(e), "error")
        except Exception as e:
            log.exception("check failed")
            self._status(f"Ошибка: {e}", "error")

    def _update_job(self, tag: str, release: dict | None) -> None:
        game_dir = Path(self.cfg["game_directory"])
        client_dir = game_dir / "client"
        tmp_dir = game_dir / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        try:
            asset = None
            if self.test_mode:
                mrpack_name = next(self.updater.dir.glob("*.mrpack")).name
            else:
                asset = self.updater.find_mrpack_asset(release)
                mrpack_name = asset["name"]
        except Exception as e:
            log.exception("get mrpack name failed")
            self._status(f"Ошибка: {e}", "error")
            return

        mrpack_path = tmp_dir / mrpack_name

        def dl_cb(done, total):
            pct = int(done / total * 100) if total else 0
            self._progress(pct, f"{mrpack_name}  {human_size(done)} / {human_size(total)}")

        try:
            if self.test_mode:
                self._status(f"Копирование {mrpack_name}...")
                self.updater.copy_asset(mrpack_path, progress_cb=dl_cb)
            else:
                self._status(f"Скачивание {mrpack_name}...")
                self.updater.download_asset(asset, mrpack_path, progress_cb=dl_cb)
        except Exception as e:
            log.exception("get mrpack failed")
            self._status(f"Ошибка получения сборки: {e}", "error")
            return

        def up_cb(stage, idx, total, msg):
            pct = int(idx / total * 100) if total else 0
            self._progress(pct, f"{msg}  ({idx}/{total})")

        try:
            self._status("Установка сборки...")
            info = self.updater.install_mrpack(mrpack_path, client_dir, progress_cb=up_cb)
        except Exception as e:
            log.exception("install mrpack failed")
            self._status(f"Ошибка установки: {e}", "error")
            return

        self._write_local_version(tag)
        self.cfg["minecraft_version"] = info.get("minecraft") or self.cfg["minecraft_version"]
        self.cfg["neoforge_version"] = info.get("neoforge") or ""
        save_config(self.cfg)

        self._status(f"Готово ({tag})", "ok")
        self._progress(100, "Готово")

    # ==================================================================
    #                              Игра
    # ==================================================================
    def _play_job(self) -> None:
        try:
            self._status("Подготовка...")
            game_dir = Path(self.cfg["game_directory"])
            mc_dir = game_dir / "minecraft"
            client_dir = game_dir / "client"
            mc_dir.mkdir(parents=True, exist_ok=True)
            client_dir.mkdir(parents=True, exist_ok=True)

            mc_version = self.cfg["minecraft_version"]
            nf_version = self.cfg.get("neoforge_version", "")
            java_path = self.cfg.get("java_path", "")
            installed = installed_version_ids(mc_dir)

            if mc_version not in installed:
                self._status("Установка Minecraft...")
                install_minecraft(mc_dir, mc_version, java_path, self._mc_progress)

            if nf_version:
                has_nf = any("neoforge" in v.lower() and nf_version in v for v in installed)
                if not has_nf:
                    self._status("Установка NeoForge...")
                    install_neoforge(mc_dir, mc_version, nf_version,
                                     java_path, self._mc_progress)

            self._status("Запуск Minecraft...")
            cmd = build_launch_command(
                mc_dir=mc_dir,
                client_dir=client_dir,
                username=self.cfg.get("username", "Player"),
                token="0",
                mc_version=mc_version,
                nf_version=nf_version,
                ram_mb=int(self.cfg.get("ram_mb", 4096)),
                java_path=java_path,
            )
            launch_minecraft(cmd, cwd=client_dir)
            self._status("Minecraft запущен", "ok")

            if self.cfg.get("close_after_launch"):
                self._ui(self.ui.quit)
        except MinecraftError as e:
            self._status(f"Ошибка: {e}", "error")
        except Exception as e:
            log.exception("play error")
            self._status(f"Ошибка: {e}", "error")

    def _mc_progress(self, status: str, current: int, total: int) -> None:
        pct = int(current / total * 100) if total else 0
        self._progress(pct, f"{status}  {current}/{total}")

    # ==================================================================
    #                        Версия установленной сборки
    # ==================================================================
    def _version_file(self) -> Path:
        return Path(self.cfg["game_directory"]) / "pack_version.txt"

    def _read_local_version(self) -> str:
        f = self._version_file()
        return f.read_text(encoding="utf-8").strip() if f.exists() else ""

    def _write_local_version(self, v: str) -> None:
        self._version_file().write_text(v, encoding="utf-8")
