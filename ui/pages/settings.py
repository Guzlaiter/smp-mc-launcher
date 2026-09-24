"""Настройки лаунчера."""
import tkinter as tk
from tkinter import filedialog, ttk

from app.config import DEFAULT_CONFIG
from ui.pages.base import BasePage
from ui.theme import C, F

RAM_MIN, RAM_MAX = 1024, 65536
RAM_STEP = 1024


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
        self.var_ram_entry = tk.StringVar(value=str(self.var_ram.get()))
        self.var_ram_pos   = tk.DoubleVar(value=self.var_ram.get())
        self.var_dir    = tk.StringVar(value=cfg.get("game_directory", ""))
        self.var_java   = tk.StringVar(value=cfg.get("java_path", ""))
        self.var_server = tk.StringVar(value=cfg.get("server_name", ""))
        self.var_close  = tk.BooleanVar(value=bool(cfg.get("close_after_launch", False)))
        self.var_auto   = tk.BooleanVar(value=bool(cfg.get("auto_check_updates", True)))

        # любое изменение «истинного» значения RAM → обновляем поле ввода
        self.var_ram.trace_add("write", self._sync_ram_entry)

        # --- вкладки ----------------------------------------------------
        # Требуется стиль "Dark.TNotebook" в ui/theme.py
        nb = ttk.Notebook(outer, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True, pady=(10, 12))

        self._build_player_tab(nb)
        self._build_game_tab(nb)
        self._build_launcher_tab(nb)

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

    # --- вкладки ----------------------------------------------------------
    def _build_player_tab(self, nb) -> None:
        tab = tk.Frame(nb, bg=C.BG)
        nb.add(tab, text="  Игрок  ")
        form = self._form(tab)
        self._row = 0
        self._section(form, "Игрок")
        self._entry(form, "Ник в игре", self.var_name)
        self._ram_row(form)

    def _build_game_tab(self, nb) -> None:
        tab = tk.Frame(nb, bg=C.BG)
        nb.add(tab, text="  Игра  ")
        form = self._form(tab)
        self._row = 0
        self._section(form, "Игра")
        self._entry(form, "Папка игры", self.var_dir, browse=self._browse_dir)
        self._entry(form, "Java (пусто = авто)", self.var_java, browse=self._browse_java)

    def _build_launcher_tab(self, nb) -> None:
        tab = tk.Frame(nb, bg=C.BG)
        nb.add(tab, text="  Лаунчер  ")
        form = self._form(tab)
        self._row = 0
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

    # --- конструктор формы ------------------------------------------------
    def _form(self, parent) -> tk.Frame:
        f = tk.Frame(parent, bg=C.BG)
        f.pack(fill="both", expand=True, padx=20, pady=20)
        f.columnconfigure(1, weight=1)
        return f

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

    # --- RAM: слайдер (шаг 1024) + ручной ввод ----------------------------
    def _ram_row(self, form) -> None:
        r = self._next()
        tk.Label(form, text="Выделяемая RAM (MB)", bg=C.BG, fg=C.TEXT, font=F.TEXT,
                 width=20, anchor="w").grid(row=r, column=0, sticky="w", pady=3)

        box = tk.Frame(form, bg=C.BG)
        box.grid(row=r, column=1, columnspan=2, sticky="ew", pady=3)
        box.columnconfigure(0, weight=1)

        # слайдер слева, растягивается
        self.scl_ram = ttk.Scale(box, from_=RAM_MIN, to=32768, orient="horizontal",
                                 variable=self.var_ram_pos, command=self._on_slider)
        self.scl_ram.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        # при отпускании мыши — «прилипаем» к сетке 1024
        self.scl_ram.bind("<ButtonRelease-1>", self._snap_slider)

        # ручной ввод
        self.ent_ram = ttk.Entry(box, textvariable=self.var_ram_entry, width=8,
                                 style="Dark.TEntry", font=F.TEXT, justify="right")
        self.ent_ram.grid(row=0, column=1, sticky="e", ipady=3)
        self.ent_ram.bind("<Return>",   self._commit_ram)
        self.ent_ram.bind("<FocusOut>", self._commit_ram)

        tk.Label(box, text="MB", bg=C.BG, fg=C.TEXT_DIM,
                 font=F.SMALL).grid(row=0, column=2, sticky="w", padx=(4, 0))

        tk.Label(box, text=f"шаг {RAM_STEP} MB · рекомендуется 4096–8192 MB",
                 bg=C.BG, fg=C.TEXT_DIM, font=F.SMALL).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def _on_slider(self, val) -> None:
        """Тянем слайдер — обновляем «истинное» значение (кратно RAM_STEP)."""
        try:
            v = int(round(float(val) / RAM_STEP) * RAM_STEP)
        except (ValueError, tk.TclError):
            return
        v = max(RAM_MIN, min(RAM_MAX, v))
        if self.var_ram.get() != v:
            self.var_ram.set(v)

    def _snap_slider(self, event=None) -> None:
        """При отпускании мыши выравниваем позицию слайдера по сетке."""
        v = max(RAM_MIN, min(RAM_MAX,
                             int(round(self.var_ram_pos.get() / RAM_STEP) * RAM_STEP)))
        self.var_ram_pos.set(v)
        self.var_ram.set(v)

    def _sync_ram_entry(self, *args) -> None:
        try:
            self.var_ram_entry.set(str(self.var_ram.get()))
        except (ValueError, tk.TclError):
            pass

    def _commit_ram(self, event=None) -> None:
        """Ручной ввод: любое значение в [RAM_MIN, RAM_MAX], слайдер подтягиваем."""
        try:
            v = int(float(self.var_ram_entry.get()))
        except (ValueError, tk.TclError):
            v = self.var_ram.get()
        v = max(RAM_MIN, min(RAM_MAX, v))
        self.var_ram.set(v)
        self.var_ram_entry.set(str(v))
        self.var_ram_pos.set(v)

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
        self.var_ram_pos.set(d["ram_mb"])
        self.var_close.set(d["close_after_launch"])
        self.var_auto.set(d["auto_check_updates"])
        self._flash("Сброшено (не сохранено)", C.TEXT_DIM)

    def _flash(self, text: str, color: str) -> None:
        self.lbl_saved.config(text=text, fg=color)
        self.after(2000, lambda: self.lbl_saved.config(text=""))

    def on_busy(self, busy: bool) -> None:
        self.btn_check.state(["disabled"] if busy else ["!disabled"])