"""
Оболочка лаунчера: сайдбар + область вкладок + строка статуса.
Сама ничего не качает и не запускает — этим занимается LauncherController.
"""
import tkinter as tk
from tkinter import messagebox

from app.controller import LauncherController, UiBridge
from ui.pages import PAGES
from ui.pages.base import PageContext
from ui.sidebar import Sidebar
from ui.statusbar import StatusBar
from ui.theme import C


class MainWindow(tk.Frame):
    def __init__(self, root, cfg: dict):
        super().__init__(root.content, bg=C.BG)
        self.pack(fill="both", expand=True)
        self.root = root
        self._current: str | None = None

        # --- правая колонка: страницы + статус ----------------------------
        right = tk.Frame(self, bg=C.BG)
        self.statusbar = StatusBar(right)
        self.statusbar.pack(side="bottom", fill="x")
        self.page_area = tk.Frame(right, bg=C.BG)
        self.page_area.pack(fill="both", expand=True)

        # --- контроллер и страницы ---------------------------------------
        self.controller = LauncherController(cfg, UiBridge(
            call=lambda fn: root.after(0, fn),
            status=self.statusbar.set_status,
            progress=self.statusbar.set_progress,
            busy=self._on_busy,
            confirm=lambda title, msg: messagebox.askyesno(title, msg),
            quit=lambda: root.after(500, root._on_close),
        ))
        ctx = PageContext(
            assets=root.assets,
            controller=self.controller,
            navigate=self.show_page,
            save_config=self._save_config,
        )
        self.pages = {cls.key: cls(self.page_area, ctx) for cls in PAGES}
        for page in self.pages.values():
            page.place(x=0, y=0, relwidth=1, relheight=1)

        # --- сайдбар + шестерёнка в заголовке -----------------------------
        self.sidebar = Sidebar(
            self, root.assets,
            tabs=[(cls.key, cls.title) for cls in PAGES],
            on_select=self.show_page,
            on_exit=root._on_close,
        )
        self.sidebar.pack(side="left", fill="y")
        right.pack(side="left", fill="both", expand=True)

        self.gear = root.add_titlebar_button(
            "settings.png", "settings_press.png",
            lambda: self.show_page("settings"))

        # Ctrl+1..9 — быстрое переключение вкладок
        for i, cls in enumerate(PAGES[:9], start=1):
            root.bind(f"<Control-Key-{i}>", lambda e, k=cls.key: self.show_page(k))

        self.show_page(PAGES[0].key)

        # --- автопроверка обновлений --------------------------------------
        if not self.controller.updater:
            self.statusbar.set_status("Источник сборки не настроен", "error")
        elif cfg.get("auto_check_updates", True):
            root.after(500, self.controller.check_updates)

    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        if key == self._current or key not in self.pages:
            return
        if self._current:
            self.pages[self._current].on_hide()
        page = self.pages[key]
        page.tkraise()
        page.on_show()
        self._current = key
        self.sidebar.set_active(key)
        self.gear.set_active(key == "settings")

    def _on_busy(self, busy: bool) -> None:
        for page in self.pages.values():
            page.on_busy(busy)

    def _save_config(self, new_cfg: dict) -> None:
        self.controller.update_config(new_cfg)
        self.root.set_title_text(new_cfg.get("server_name") or "Launcher")
        # сразу отражаем изменения на открытой вкладке (если нужно)
        if self._current:
            self.pages[self._current].on_show()
