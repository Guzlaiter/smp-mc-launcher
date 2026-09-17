import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from app.config import (
    load_config, save_config, GITHUB_REPO, TEST_RELEASE_DIR, is_test_mode,
)
from app.github_updater import GithubUpdater, LocalUpdater, UpdateError
from app.minecraft import (
    MinecraftError,
    install_minecraft,
    install_neoforge,
    build_launch_command,
    launch_minecraft,
    installed_version_ids,
)
from app.utils import log, human_size
from ui.settings import SettingsDialog


class MainWindow(ttk.Frame):
    def __init__(self, master, cfg: dict):
        super().__init__(master, padding=15)
        self.cfg = cfg
        self.pack(fill="both", expand=True)

        self.test_mode = is_test_mode()
        if self.test_mode:
            self.updater = LocalUpdater(TEST_RELEASE_DIR)
            log.info(f"Тестовый режим: релиз из {TEST_RELEASE_DIR}")
        else:
            self.updater = GithubUpdater(GITHUB_REPO) if GITHUB_REPO and "/" in GITHUB_REPO else None
            if not self.updater:
                log.warning("GITHUB_REPO не задан в app/config.py")

        self._build_ui()

        if self.updater and self.cfg.get("auto_check_updates", True):
            self.after(200, self._check_updates_async)
        elif not self.updater:
            self._set_status("Источник сборки не настроен", "red")

    # ---------------- UI ----------------

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text=self.cfg.get("server_name", "MY SERVER"),
                  font=("Segoe UI", 14, "bold")).pack(side="left")
        if self.test_mode:
            ttk.Label(top, text="[ТЕСТ]", foreground="orange").pack(side="right")

        ttk.Separator(self).pack(fill="x", pady=10)

        info = ttk.Frame(self)
        info.pack(fill="x")
        self.lbl_mc = ttk.Label(info, text=f"Minecraft {self.cfg['minecraft_version']}")
        self.lbl_mc.pack(anchor="w")
        self.lbl_nf = ttk.Label(info, text=f"NeoForge {self.cfg.get('neoforge_version') or '—'}")
        self.lbl_nf.pack(anchor="w")
        self.lbl_build = ttk.Label(info, text="Сборка: —")
        self.lbl_build.pack(anchor="w")

        self.lbl_status = ttk.Label(self, text="Статус: —", foreground="gray")
        self.lbl_status.pack(pady=15)

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 5))

        self.lbl_progress = ttk.Label(self, text="", foreground="gray")
        self.lbl_progress.pack()

        self.btn_play = ttk.Button(self, text="ИГРАТЬ", command=self._on_play, state="disabled")
        self.btn_play.pack(pady=20, ipadx=40, ipady=8)

        row = ttk.Frame(self)
        row.pack(fill="x")
        self.btn_update = ttk.Button(row, text="Проверить обновления",
                                     command=self._check_updates_async)
        self.btn_update.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.btn_verify = ttk.Button(row, text="Проверить целостность",
                                     command=self._verify_integrity)
        self.btn_verify.pack(side="left", expand=True, fill="x", padx=(5, 0))

        ttk.Separator(self).pack(fill="x", pady=10)
        bottom = ttk.Frame(self)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Настройки", command=self._open_settings).pack(side="left")
        ttk.Button(bottom, text="Открыть папку", command=self._open_folder).pack(side="right")

    def _set_status(self, text: str, color: str = "black"):
        self.lbl_status.config(text=f"Статус: {text}", foreground=color)

    def _update_progress(self, pct: int, text: str = ""):
        self.progress.config(value=max(0, min(100, pct)))
        self.lbl_progress.config(text=text)

    # ---------------- Обновление ----------------

    def _check_updates_async(self):
        if not self.updater:
            self._set_status("Источник сборки не настроен", "red")
            return
        self.btn_play.config(state="disabled")
        self.btn_update.config(state="disabled")
        threading.Thread(target=self._check_updates, daemon=True).start()

    def _check_updates(self):
        try:
            self.after(0, lambda: self._set_status("Проверка источника...", "black"))

            if self.test_mode:
                tag = self.updater.get_local_version()
                log.info(f"Локальный релиз: {tag}")
            else:
                release = self.updater.get_latest_release()
                tag = release.get("tag_name", "?")
                log.info(f"GitHub: последний релиз {tag}")

            local_ver = self._read_local_version()
            self.after(0, lambda: self.lbl_build.config(text=f"Сборка: {tag}"))
            self.after(0, lambda: self.btn_update.config(state="normal"))

            if local_ver == tag:
                self.after(0, lambda: self._set_status(f"Сборка актуальна ({tag})", "green"))
                self.after(0, lambda: self.btn_play.config(state="normal"))
                return

            self.after(0, lambda: self._set_status(
                f"Доступна версия {tag}. Нажмите «Обновить».", "orange"
            ))
            if messagebox.askyesno(
                "Обновление",
                f"Доступна новая версия сборки {tag}.\nОбновить сейчас?"
            ):
                self._do_update(tag)
            else:
                self.after(0, lambda: self.btn_play.config(state="normal"))
        except UpdateError as e:
            msg = str(e)
            self.after(0, lambda m=msg: self._set_status(m, "red"))
            self.after(0, lambda: self.btn_update.config(state="normal"))
        except Exception as e:
            log.exception("check failed")
            msg = f"Ошибка: {e}"
            self.after(0, lambda m=msg: self._set_status(m, "red"))
            self.after(0, lambda: self.btn_update.config(state="normal"))

    def _verify_integrity(self):
        if not self.updater:
            self._set_status("Источник сборки не настроен", "red")
            return
        self.btn_play.config(state="disabled")
        self.btn_update.config(state="disabled")
        self.btn_verify.config(state="disabled")
        threading.Thread(target=self._verify_worker, daemon=True).start()

    def _verify_worker(self):
        try:
            if self.test_mode:
                tag = self.updater.get_local_version()
            else:
                release = self.updater.get_latest_release()
                tag = release.get("tag_name", "?")
            self.after(0, lambda: self._set_status(f"Проверка целостности ({tag})...", "black"))
            self._run_update_worker(tag)
        except Exception as e:
            log.exception("verify failed")
            msg = f"Ошибка: {e}"
            self.after(0, lambda m=msg: self._set_status(m, "red"))
        finally:
            self.after(0, lambda: self.btn_update.config(state="normal"))
            self.after(0, lambda: self.btn_verify.config(state="normal"))
            self.after(0, lambda: self.btn_play.config(state="normal"))

    def _do_update(self, tag: str):
        self.btn_play.config(state="disabled")
        self.btn_update.config(state="disabled")
        self.btn_verify.config(state="disabled")
        threading.Thread(target=self._update_worker, args=(tag,), daemon=True).start()

    def _update_worker(self, tag: str):
        self._run_update_worker(tag)

    def _run_update_worker(self, tag: str):
        game_dir = Path(self.cfg["game_directory"])
        client_dir = game_dir / "client"
        tmp_dir = game_dir / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # имя mrpack
        if self.test_mode:
            mrpack_name = next(self.updater.dir.glob("*.mrpack")).name
        else:
            release = self.updater.get_latest_release()
            asset = self.updater.find_mrpack_asset(release)
            mrpack_name = asset["name"]

        mrpack_path = tmp_dir / mrpack_name

        # 1. Получить mrpack
        def dl_cb(done, total):
            pct = int(done / total * 100) if total else 0
            self.after(0, lambda: self._update_progress(
                pct, f"Получение {mrpack_name}  {human_size(done)} / {human_size(total)}"
            ))

        try:
            if self.test_mode:
                self.after(0, lambda: self._set_status(f"Копирование {mrpack_name}...", "black"))
                self.updater.copy_asset(mrpack_path, progress_cb=dl_cb)
            else:
                release = self.updater.get_latest_release()
                asset = self.updater.find_mrpack_asset(release)
                self.after(0, lambda: self._set_status(f"Скачивание {mrpack_name}...", "black"))
                self.updater.download_asset(asset, mrpack_path, progress_cb=dl_cb)
        except Exception as e:
            log.exception("get mrpack failed")
            msg = f"Ошибка получения сборки: {e}"
            self.after(0, lambda m=msg: self._set_status(m, "red"))
            return

        # 2. Установить
        def up_cb(stage, idx, total, msg):
            pct = int(idx / total * 100) if total else 0
            self.after(0, lambda: self._update_progress(pct, f"{msg}\n{idx} / {total} файлов"))

        try:
            self.after(0, lambda: self._set_status("Установка сборки...", "black"))
            info = self.updater.install_mrpack(mrpack_path, client_dir, progress_cb=up_cb)
            log.info(f"Сборка установлена: {info}")
        except Exception as e:
            log.exception("install mrpack failed")
            msg = f"Ошибка установки: {e}"
            self.after(0, lambda m=msg: self._set_status(m, "red"))
            return

        # 3. Сохранить версию и конфиг
        self._write_local_version(tag)
        self.cfg["minecraft_version"] = info.get("minecraft") or self.cfg["minecraft_version"]
        self.cfg["neoforge_version"] = info.get("neoforge") or ""
        save_config(self.cfg)

        self.after(0, lambda: self.lbl_mc.config(text=f"Minecraft {self.cfg['minecraft_version']}"))
        self.after(0, lambda: self.lbl_nf.config(
            text=f"NeoForge {self.cfg['neoforge_version'] or '—'}"
        ))
        self.after(0, lambda: self.lbl_build.config(text=f"Сборка: {tag}"))

        dl = info.get("downloaded", 0)
        sk = info.get("skipped", 0)
        fl = info.get("failed", 0)
        color = "orange" if fl else "green"
        text = f"Готово ({tag}). Скачано: {dl}, уже было: {sk}" + (f", ошибок: {fl}" if fl else "")
        self.after(0, lambda: self._set_status(text, color))
        self.after(0, lambda: self._update_progress(100, "Готово"))

    # ---------------- Локальная версия ----------------

    def _version_file(self) -> Path:
        return Path(self.cfg["game_directory"]) / "pack_version.txt"

    def _read_local_version(self) -> str:
        f = self._version_file()
        return f.read_text(encoding="utf-8").strip() if f.exists() else ""

    def _write_local_version(self, v: str) -> None:
        self._version_file().write_text(v, encoding="utf-8")

    # ---------------- Игра ----------------

    def _on_play(self):
        self.btn_play.config(state="disabled")
        self._set_status("Подготовка...", "black")
        threading.Thread(target=self._play, daemon=True).start()

    def _play(self):
        try:
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
                self.after(0, lambda: self._set_status("Установка Minecraft...", "black"))
                install_minecraft(mc_dir, mc_version, java_path, self._mc_progress)

            if nf_version:
                has_nf = any("neoforge" in v.lower() and nf_version in v for v in installed)
                if not has_nf:
                    self.after(0, lambda: self._set_status("Установка NeoForge...", "black"))
                    install_neoforge(mc_dir, mc_version, nf_version, java_path, self._mc_progress)

            self.after(0, lambda: self._set_status("Запуск Minecraft...", "black"))
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

            self.after(0, lambda: self._set_status("Minecraft запущен", "green"))
            if self.cfg.get("close_after_launch"):
                self.after(500, self.master.destroy)
            else:
                self.after(0, lambda: self.btn_play.config(state="normal"))
        except MinecraftError as e:
            msg = f"Ошибка: {e}"
            self.after(0, lambda m=msg: self._set_status(m, "red"))
            self.after(0, lambda: self.btn_play.config(state="normal"))
        except Exception as e:
            log.exception("play error")
            msg = f"Ошибка: {e}"
            self.after(0, lambda m=msg: self._set_status(m, "red"))
            self.after(0, lambda: self.btn_play.config(state="normal"))

    def _mc_progress(self, status: str, current: int, total: int):
        pct = int(current / total * 100) if total else 0
        text = f"{status}  {current}/{total}"
        self.after(0, lambda: self._update_progress(pct, text))

    # ---------------- Разное ----------------

    def _open_settings(self):
        SettingsDialog(self, self.cfg, on_save=self._save_settings)

    def _save_settings(self, new_cfg):
        self.cfg = new_cfg
        save_config(self.cfg)
        self.lbl_mc.config(text=f"Minecraft {self.cfg['minecraft_version']}")
        self.lbl_nf.config(text=f"NeoForge {self.cfg.get('neoforge_version') or '—'}")
        self.master.title(f"{self.cfg.get('server_name', 'MY SERVER')} — Launcher")
        messagebox.showinfo("Настройки", "Сохранено")

    def _open_folder(self):
        import os
        p = Path(self.cfg["game_directory"])
        p.mkdir(parents=True, exist_ok=True)
        os.startfile(str(p))