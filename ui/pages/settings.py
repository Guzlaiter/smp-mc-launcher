"""Настройки лаунчера."""
import tkinter as tk
from tkinter import filedialog, ttk

from app.config import DEFAULT_CONFIG
from ui.pages.base import BasePage
from ui.theme import C, F

RAM_MIN, RAM_MAX = 1024, 65536


class SettingsPage(BasePage):
    key = "settings"
    title = "Настройки"

    # ------------------------------------------------------------------
    def build(self) -> None:
        outer = tk.Frame(self, bg=C.BG)
        outer.pack(fill="both", expand=True, padx=36, pady=24)

        tk.Label(outer, text="НАСТРОЙКИ ЛАУНЧЕРА", bg=C.BG, fg=C.ACCENT,
                 font=F.H1).pack(anchor="w")
        tk.Frame(outer, bg=C.ACCENT, height=2).pack(fill="x", pady=(4, 6))

        # --- переменные -------------------------------------------------
        cfg = self.ctx.controller.cfg
        self.var_name   = tk.StringVar(value=cfg.get("username", ""))
        self.var_ram    = tk.IntVar(value=int(cfg.get("ram_mb", 4096)))
        self.var_dir    = tk.StringVar(value=cfg.get("game_directory", ""))
        self.var_java   = tk.StringVar(value=cfg.get("java_path", ""))
        self.var_server = tk.StringVar(value=cfg.get("server_name", ""))
        self.var_close  = tk.BooleanVar(value=bool(cfg.get("close_after_launch", False)))
        self.var_auto   = tk.BooleanVar(value=bool(cfg.get("auto_check_updates", True)))

        # --- форма: label | поле | кнопка --------------------------------
        form = tk.Frame(outer, bg=C.BG)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self._row = 0

        self._section(form, "Игрок")
        self._entry(form, "Ник в игре", self.var_name)
        self._ram_row(form)

        self._section(form, "Игра")
        self._entry(form, "Папка игры", self.var_dir, browse=self._browse_dir)
        self._entry(form, "Java (пусто = авто)", self.var_java, browse=self._browse_java)

        self._section(form, "Лаунчер")
        self._entry(form, "Название в окне", self.var_server)

        checks = tk.Frame(form, bg=C.BG)
        checks.grid(row=self._next(), column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Checkbutton(checks, text="Закрывать лаунчер после запуска игры",
                        variable=self.var_close, style="Dark.TCheckbutton").pack(anchor="w", pady=2)
        ttk.Checkbutton(checks, text="Проверять обновления при запуске",
                        variable=self.var_auto, style="Dark.TCheckbutton").pack(anchor="w", pady=2)

        self.btn_check = ttk.Button(form, text="Проверить обновления сейчас",
                                    style="Dark.TButton",
                                    command=self.ctx.controller.check_updates)
        self.btn_check.grid(row=self._next(), column=0, columnspan=3, sticky="w", pady=(8, 0))

        # --- низ: Сбросить ... статус ... Сохранить ----------------------
        bar = tk.Frame(outer, bg=C.BG)
        bar.pack(fill="x", side="bottom")
        ttk.Button(bar, text="Сбросить", style="Dark.TButton",
                   command=self._reset).pack(side="left")
        ttk.Button(bar, text="Сохранить", style="Accent.TButton",
                   command=self._save).pack(side="right")
        self.lbl_saved = tk.Label(bar, text="", bg=C.BG, fg=C.ACCENT,
                                  font=("Arial", 9, "italic"))
        self.lbl_saved.pack(side="right", padx=15)

    # --- конструктор формы ------------------------------------------------
    def _next(self) -> int:
        self._row += 1
        return self._row - 1

    def _section(self, form, text: str) -> None:
        r = self._next()
        tk.Label(form, text=text.upper(), bg=C.BG, fg=C.ACCENT,
                 font=F.SMALL_B).grid(row=r, column=0, columnspan=3, sticky="w", pady=(14, 2))
        tk.Frame(form, bg=C.BORDER, height=1).grid(row=self._next(), column=0,
                                                   columnspan=3, sticky="ew", pady=(0, 4))

    def _entry(self, form, label: str, var: tk.StringVar, browse=None) -> None:
        r = self._next()
        tk.Label(form, text=label, bg=C.BG, fg=C.TEXT, font=F.TEXT,
                 width=20, anchor="w").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=var, style="Dark.TEntry", font=F.TEXT).grid(
            row=r, column=1, sticky="ew", ipady=4, pady=3)
        if browse:
            ttk.Button(form, text="Обзор...", style="Dark.TButton",
                       command=browse).grid(row=r, column=2, padx=(8, 0), pady=3)

    def _ram_row(self, form) -> None:
        r = self._next()
        tk.Label(form, text="Выделяемая RAM (MB)", bg=C.BG, fg=C.TEXT, font=F.TEXT,
                 width=20, anchor="w").grid(row=r, column=0, sticky="w", pady=3)
        box = tk.Frame(form, bg=C.BG)
        box.grid(row=r, column=1, sticky="w", pady=3)
        ttk.Spinbox(box, from_=RAM_MIN, to=32768, increment=512, textvariable=self.var_ram,
                    style="Dark.TSpinbox", font=F.TEXT, width=10).pack(side="left")
        tk.Label(box, text="   рекомендуется 4096–8192 MB", bg=C.BG, fg=C.TEXT_DIM,
                 font=F.SMALL).pack(side="left")

    # --- обработчики -------------------------------------------------------
    def _browse_dir(self) -> None:
        p = filedialog.askdirectory(title="Выберите папку игры",
                                    initialdir=self.var_dir.get() or ".")
        if p:
            self.var_dir.set(p)

    def _browse_java(self) -> None:
        p = filedialog.askopenfilename(
            title="Выберите java.exe",
            filetypes=[("java.exe", "java.exe"), ("Все файлы", "*.*")])
        if p:
            self.var_java.set(p)

    def _save(self) -> None:
        try:
            ram = int(self.var_ram.get())
        except (ValueError, tk.TclError):
            ram = DEFAULT_CONFIG["ram_mb"]
        ram = max(RAM_MIN, min(RAM_MAX, ram))
        self.var_ram.set(ram)

        # Берём СВЕЖИЙ конфиг: за время работы окна обновление сборки могло
        # поменять версии MC/NeoForge — их нельзя затирать старой копией.
        new = dict(self.ctx.controller.cfg)
        new.update(
            username=self.var_name.get().strip() or DEFAULT_CONFIG["username"],
            server_name=self.var_server.get().strip() or DEFAULT_CONFIG["server_name"],
            game_directory=self.var_dir.get().strip() or DEFAULT_CONFIG["game_directory"],
            java_path=self.var_java.get().strip(),
            ram_mb=ram,
            close_after_launch=bool(self.var_close.get()),
            auto_check_updates=bool(self.var_auto.get()),
        )
        self.ctx.save_config(new)
        self._flash("✓ Сохранено", C.ACCENT)

    def _reset(self) -> None:
        """Полей касается только форма; в конфиг попадёт после «Сохранить»."""
        d = DEFAULT_CONFIG
        self.var_name.set(d["username"])
        self.var_server.set(d["server_name"])
        self.var_dir.set(d["game_directory"])
        self.var_java.set(d["java_path"])
        self.var_ram.set(d["ram_mb"])
        self.var_close.set(d["close_after_launch"])
        self.var_auto.set(d["auto_check_updates"])
        self._flash("Сброшено (не сохранено)", C.TEXT_DIM)

    def _flash(self, text: str, color: str) -> None:
        self.lbl_saved.config(text=text, fg=color)
        self.after(2000, lambda: self.lbl_saved.config(text=""))

    def on_busy(self, busy: bool) -> None:
        self.btn_check.state(["disabled"] if busy else ["!disabled"])
