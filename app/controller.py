"""
Логика лаунчера без tkinter: проверка/установка обновлений сборки и запуск игры.

С интерфейсом общается только через UiBridge — контроллер не знает ни про окна, ни про цвета.
Тяжёлые операции идут в фоновом потоке; одновременно выполняется только одна
(нельзя нажать PLAY во время обновления).
"""
from __future__ import annotations

import shutil
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.config import GITHUB_BRANCH, GITHUB_REPO, TEST_RELEASE_DIR, is_test_mode, save_config
from app.github_updater import (
    GithubUpdater,
    LocalUpdater,
    UpdateError,
    check_pack,
    install_pack,
    remove_old_pack,
    save_manifest,
)
from app.minecraft import (
    MinecraftError,
    build_launch_command,
    install_minecraft,
    install_neoforge,
    installed_version_ids,
    launch_minecraft,
)
from app.diagnostics import check_hosts, format_report, summarize
from app.utils import describe_error, human_size, log


def _short(tag: str) -> str:
    """Хэш коммита показываем как 7 символов; обычные версии («v1.2») — как есть."""
    return tag[:7] if len(tag) == 40 and all(c in "0123456789abcdef" for c in tag) else tag


@dataclass
class UiBridge:
    """Что контроллеру нужно от интерфейса. Все вызовы приходят в UI-потоке (кроме call)."""
    call: Callable[[Callable[[], None]], None]   # выполнить функцию в UI-потоке
    status: Callable[[str, str], None]           # (текст, уровень: info|ok|warn|error)
    progress: Callable[[int, str], None]         # (процент, текст)
    busy: Callable[[bool], None]                 # идёт ли операция
    confirm: Callable[[str, str], bool]          # диалог да/нет
    quit: Callable[[], None]                     # закрыть лаунчер
    report: Callable[[str, str], None] = lambda title, text: None   # показать окно с отчётом


class LauncherController:
    def __init__(self, cfg: dict, ui: UiBridge):
        self.cfg = cfg
        self.ui = ui
        self._lock = threading.Lock()          # «тяжёлая» операция: установка сборки / запуск игры
        self._check_lock = threading.Lock()    # проверка обновлений (PLAY не блокирует)
        self._diag_lock = threading.Lock()     # диагностика сети

        self.test_mode = is_test_mode()
        if self.test_mode:
            self.updater = LocalUpdater(TEST_RELEASE_DIR)
        else:
            configured = "/" in GITHUB_REPO and GITHUB_REPO != "owner/repo"
            self.updater = GithubUpdater(GITHUB_REPO, GITHUB_BRANCH) if configured else None

    # ==================================================================
    #                           Публичное API
    # ==================================================================
    def update_config(self, new_cfg: dict) -> None:
        self.cfg = new_cfg
        save_config(new_cfg)

    def version_label(self) -> str:
        return f"NeoForge | MC {self.cfg.get('minecraft_version', '?')}"

    def check_updates(self) -> None:
        """Проверка обновлений. Идёт в фоне и НЕ блокирует кнопку PLAY."""
        if not self.updater:
            self._status("Источник сборки не настроен: укажите GITHUB_REPO в app/config.py", "error")
            return
        if not self._check_lock.acquire(blocking=False):
            self._status("Проверка уже идёт", "warn")
            return
        threading.Thread(target=self._check_thread, daemon=True).start()

    def play(self) -> None:
        threading.Thread(target=self._play_thread, daemon=True).start()

    def diagnose(self) -> None:
        """Проверяет доступность GitHub / Modrinth / Mojang / NeoForge. Не блокирует PLAY."""
        if not self._diag_lock.acquire(blocking=False):
            self._status("Диагностика уже идёт", "warn")
            return
        threading.Thread(target=self._diag_thread, daemon=True).start()

    # ==================================================================
    #                    Потоки / общение с UI
    # ==================================================================
    @contextmanager
    def _exclusive(self):
        """Одновременно — только одна тяжёлая операция; на её время UI получает busy=True."""
        got = self._lock.acquire(blocking=False)
        if got:
            self._ui(lambda: self.ui.busy(True))
            self._progress(0, "")
        try:
            yield got
        finally:
            if got:
                self._lock.release()
                self._ui(lambda: self.ui.busy(False))

    def _check_thread(self) -> None:
        try:
            self._check_job()
        except UpdateError as e:
            self._status_bg(str(e), "error")
        except Exception as e:
            log.exception("check failed")
            self._status_bg(f"Проверка обновлений: {describe_error(e)}", "error")
        finally:
            self._check_lock.release()

    def _diag_thread(self) -> None:
        try:
            self._status_bg("Диагностика сети...")
            results = check_hosts()
            text = format_report(results)
            log.info("Диагностика сети:\n" + text)
            self._status(*summarize(results))
            self._ui(lambda: self.ui.report("Диагностика сети", text))
        except Exception as e:
            log.exception("diagnose failed")
            self._status(f"Диагностика: {describe_error(e)}", "error")
        finally:
            self._diag_lock.release()

    def _play_thread(self) -> None:
        with self._exclusive() as ok:
            if not ok:
                self._status("Дождитесь завершения текущей операции", "warn")
                return
            self._play_job()

    def _status_bg(self, text: str, level: str = "info") -> None:
        """Статус от фоновой проверки: не перебивает сообщения идущей установки/запуска."""
        if self._lock.locked():
            log.info(f"(фон) {text}")
        else:
            self._status(text, level)

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
        source = "test_release" if self.test_mode else "GitHub"
        self._status_bg(f"Проверка обновлений ({source})...")

        tag = self.updater.latest_version()
        shown = _short(tag)

        if self._read_local_version() == tag:
            self._status_bg(f"Сборка актуальна ({shown})", "ok")
            return

        self._status_bg(f"Доступна версия {shown}", "warn")
        if not self._confirm("Обновление",
                             f"Доступна новая версия сборки {shown}.\nОбновить сейчас?"):
            return

        with self._exclusive() as ok:
            if not ok:
                self._status("Обновление отложено: идёт запуск игры", "warn")
                return
            try:
                self._update_job(tag)
            except UpdateError as e:
                self._status(str(e), "error")
            except Exception as e:
                log.exception("update failed")
                self._status(f"Ошибка обновления: {describe_error(e)}", "error")

    def _update_job(self, tag: str) -> None:
        game_dir = Path(self.cfg["game_directory"])
        client_dir = game_dir / "client"
        work_dir = game_dir / "tmp"

        def dl_cb(done, total):
            if total:
                self._progress(int(done / total * 100),
                               f"Скачивание  {human_size(done)} / {human_size(total)}")
            else:  # codeload не сообщает размер архива заранее
                self._progress(0, f"Скачивание  {human_size(done)}")

        def up_cb(stage, idx, total, msg):
            pct = int(idx / total * 100) if total else 0
            self._progress(pct, f"{msg}  ({idx}/{total})")

        try:
            self._status("Загрузка сборки из test_release..." if self.test_mode
                         else "Скачивание сборки с GitHub...")
            root = self.updater.fetch(work_dir, progress_cb=dl_cb)
        except Exception as e:
            log.exception("fetch pack failed")
            self._status(str(e) if isinstance(e, UpdateError)
                         else f"Ошибка получения сборки: {describe_error(e)}", "error")
            return

        try:
            # Новая сборка уже скачана. Сначала убеждаемся, что она рабочая, и только потом
            # убираем старую (иначе пустой/битый репозиторий оставил бы игрока без сборки)
            check_pack(root)
            self._status("Удаление старой сборки...")
            self._progress(0, "")
            remove_old_pack(client_dir, self._manifest_file())

            self._status("Установка новой сборки...")
            info = install_pack(root, client_dir, up_cb)
            # запоминаем, что именно поставили — при следующем обновлении удалим ровно это
            save_manifest(self._manifest_file(), info.get("files", []), tag)
        except Exception as e:
            log.exception("install pack failed")
            self._status(str(e) if isinstance(e, UpdateError)
                         else f"Ошибка установки: {describe_error(e)}", "error")
            return
        finally:
            if not self.test_mode:  # скачанную копию репозитория не храним (test_release не трогаем!)
                shutil.rmtree(work_dir / "repo", ignore_errors=True)

        # Версии из сборки: mrpack задаёт обе всегда, pack.json — только то, что указал
        if info.get("minecraft"):
            self.cfg["minecraft_version"] = info["minecraft"]
        if "neoforge" in info:
            self.cfg["neoforge_version"] = info["neoforge"] or ""
        save_config(self.cfg)

        failed = int(info.get("failed", 0))
        if failed:
            # Часть файлов не скачалась (сеть): версию НЕ записываем, чтобы при следующей
            # проверке лаунчер предложил докачать. Уже скачанные файлы пропустятся по хэшу.
            log.error(f"Сборка {tag} установлена не полностью: не скачано {failed} файлов")
            self._status(f"Не скачано файлов: {failed}. Проверьте сеть (Настройки → Диагностика) "
                         f"и повторите обновление", "error")
            return

        self._write_local_version(tag)
        self._status(f"Готово ({_short(tag)})", "ok")
        self._progress(100, "Готово")

    # ==================================================================
    #                              Игра
    # ==================================================================
    def _play_job(self) -> None:
        stage = "Подготовка"
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
                stage = "Установка Minecraft"
                self._status("Установка Minecraft...")
                install_minecraft(mc_dir, mc_version, java_path, self._mc_progress)

            if nf_version:
                has_nf = any("neoforge" in v.lower() and nf_version in v for v in installed)
                if not has_nf:
                    stage = "Установка NeoForge"
                    self._status("Установка NeoForge...")
                    install_neoforge(mc_dir, mc_version, nf_version,
                                     java_path, self._mc_progress)

            stage = "Запуск Minecraft"
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
            self._status(f"{stage}: {e}", "error")
        except Exception as e:
            log.exception(f"play error ({stage})")
            self._status(f"{stage}: {describe_error(e)}", "error")

    def _mc_progress(self, status: str, current: int, total: int) -> None:
        pct = int(current / total * 100) if total else 0
        self._progress(pct, f"{status}  {current}/{total}")

    # ==================================================================
    #                        Версия установленной сборки
    # ==================================================================
    def _manifest_file(self) -> Path:
        """Список файлов установленной сборки (лежит рядом с client/, не внутри)."""
        return Path(self.cfg["game_directory"]) / "pack_files.json"

    def _version_file(self) -> Path:
        return Path(self.cfg["game_directory"]) / "pack_version.txt"

    def _read_local_version(self) -> str:
        f = self._version_file()
        return f.read_text(encoding="utf-8").strip() if f.exists() else ""

    def _write_local_version(self, v: str) -> None:
        self._version_file().write_text(v, encoding="utf-8")
