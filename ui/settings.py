# ui/settings.py
import tkinter as tk
from tkinter import ttk, filedialog


class SettingsTab(tk.Frame):
    """
    Вкладка настроек для лаунчера.
    Использование:
        tab = SettingsTab(parent, cfg=config_dict, on_save=callback)
        tab.pack(fill="both", expand=True)
    """

    # --- Цвета (в стиле лаунчера) ---
    BG          = "#2b2b2b"     # основной фон
    PANEL_BG    = "#1f1f1f"     # фон полей ввода
    ACCENT      = "#8B5A2B"     # медный акцент
    ACCENT_HOV  = "#A56A35"     # акцент при наведении
    TEXT        = "#e0e0e0"     # основной текст
    TEXT_DIM    = "#888888"     # второстепенный текст
    BORDER      = "#3a3a3a"     # границы
    BUTTON_BG   = "#3a3a3a"     # фон кнопок
    BUTTON_HOV  = "#4a4a4a"     # кнопка при наведении

    def __init__(self, master, cfg: dict, on_save):
        super().__init__(master, bg=self.BG)
        self.cfg = dict(cfg)
        self.on_save = on_save

        # --- Настройка стилей ttk под тёмную тему ---
        self._setup_ttk_style()

        # --- Контент ---
        self._build_ui()

    # ------------------------------------------------------------------
    # Стили ttk
    # ------------------------------------------------------------------
    def _setup_ttk_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")  # позволяет кастомизировать цвета
        except tk.TclError:
            pass

        # Рамка/фон
        style.configure("Dark.TFrame", background=self.BG)
        style.configure("Dark.TLabel", background=self.BG, foreground=self.TEXT)
        style.configure("DarkDim.TLabel", background=self.BG, foreground=self.TEXT_DIM)
        style.configure("Accent.TLabel", background=self.BG, foreground=self.ACCENT,
                        font=("Arial", 11, "bold"))

        # Поля ввода
        style.configure("Dark.TEntry",
                        fieldbackground=self.PANEL_BG,
                        background=self.PANEL_BG,
                        foreground=self.TEXT,
                        insertcolor=self.TEXT,
                        bordercolor=self.BORDER,
                        lightcolor=self.BORDER,
                        darkcolor=self.BORDER,
                        relief="flat")
        style.map("Dark.TEntry",
                  fieldbackground=[("focus", "#252525")],
                  bordercolor=[("focus", self.ACCENT)])

        # Спинбокс
        style.configure("Dark.TSpinbox",
                        fieldbackground=self.PANEL_BG,
                        background=self.PANEL_BG,
                        foreground=self.TEXT,
                        arrowcolor=self.TEXT,
                        bordercolor=self.BORDER,
                        lightcolor=self.BORDER,
                        darkcolor=self.BORDER,
                        relief="flat")
        style.map("Dark.TSpinbox",
                  fieldbackground=[("focus", "#252525")],
                  bordercolor=[("focus", self.ACCENT)])

        # Чекбоксы
        style.configure("Dark.TCheckbutton",
                        background=self.BG,
                        foreground=self.TEXT,
                        focuscolor=self.BG,
                        indicatorcolor=self.PANEL_BG)
        style.map("Dark.TCheckbutton",
                  background=[("active", self.BG)],
                  foreground=[("active", self.ACCENT)],
                  indicatorcolor=[("selected", self.ACCENT),
                                  ("active", self.ACCENT)])

        # Кнопки
        style.configure("Dark.TButton",
                        background=self.BUTTON_BG,
                        foreground=self.TEXT,
                        bordercolor=self.BORDER,
                        lightcolor=self.BUTTON_BG,
                        darkcolor=self.BUTTON_BG,
                        relief="flat",
                        padding=(12, 6))
        style.map("Dark.TButton",
                  background=[("active", self.BUTTON_HOV)],
                  foreground=[("active", self.TEXT)])

        style.configure("Accent.TButton",
                        background=self.ACCENT,
                        foreground="white",
                        bordercolor=self.ACCENT,
                        lightcolor=self.ACCENT,
                        darkcolor=self.ACCENT,
                        relief="flat",
                        padding=(14, 6),
                        font=("Arial", 10, "bold"))
        style.map("Accent.TButton",
                  background=[("active", self.ACCENT_HOV)],
                  foreground=[("active", "white")])

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def _build_ui(self):
        # Основной контейнер с отступами
        outer = tk.Frame(self, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=40, pady=30)

        # Заголовок
        tk.Label(outer, text="НАСТРОЙКИ ЛАУНЧЕРА",
                 bg=self.BG, fg=self.ACCENT,
                 font=("Arial", 18, "bold")).pack(anchor="w", pady=(0, 5))
        tk.Frame(outer, bg=self.ACCENT, height=2).pack(fill="x", pady=(0, 20))

        # Сетка для полей (label сверху, поле снизу)
        form = tk.Frame(outer, bg=self.BG)
        form.pack(fill="x")

        # --- Ник в игре ---
        self._add_label(form, "Ник в игре")
        self.var_name = tk.StringVar(value=self.cfg.get("username", "Player"))
        ttk.Entry(form, textvariable=self.var_name, style="Dark.TEntry",
                  font=("Arial", 10)).pack(fill="x", pady=(0, 15), ipady=6)

        # --- Название в окне ---
        self._add_label(form, "Название в окне лаунчера")
        self.var_server = tk.StringVar(value=self.cfg.get("server_name", "MY SERVER"))
        ttk.Entry(form, textvariable=self.var_server, style="Dark.TEntry",
                  font=("Arial", 10)).pack(fill="x", pady=(0, 15), ipady=6)

        # --- Папка игры ---
        self._add_label(form, "Папка игры (.minecraft)")
        row_dir = tk.Frame(form, bg=self.BG)
        row_dir.pack(fill="x", pady=(0, 15))
        self.var_dir = tk.StringVar(value=self.cfg.get("game_directory", ""))
        ttk.Entry(row_dir, textvariable=self.var_dir, style="Dark.TEntry",
                  font=("Arial", 10)).pack(side="left", fill="x", expand=True, ipady=6)
        ttk.Button(row_dir, text="Обзор...", style="Dark.TButton",
                   command=self._browse_dir).pack(side="left", padx=(8, 0))

        # --- Java ---
        self._add_label(form, "Java (пусто = автоопределение)")
        row_java = tk.Frame(form, bg=self.BG)
        row_java.pack(fill="x", pady=(0, 15))
        self.var_java = tk.StringVar(value=self.cfg.get("java_path", ""))
        ttk.Entry(row_java, textvariable=self.var_java, style="Dark.TEntry",
                  font=("Arial", 10)).pack(side="left", fill="x", expand=True, ipady=6)
        ttk.Button(row_java, text="Обзор...", style="Dark.TButton",
                   command=self._browse_java).pack(side="left", padx=(8, 0))

        # --- RAM ---
        self._add_label(form, "Выделяемая RAM (MB)")
        row_ram = tk.Frame(form, bg=self.BG)
        row_ram.pack(fill="x", pady=(0, 15))
        self.var_ram = tk.IntVar(value=int(self.cfg.get("ram_mb", 4096)))
        ttk.Spinbox(row_ram, from_=1024, to=32768, increment=512,
                    textvariable=self.var_ram, style="Dark.TSpinbox",
                    font=("Arial", 10), width=10).pack(side="left", ipady=6)
        tk.Label(row_ram, text="  (рекомендуется 4096–8192 MB)",
                 bg=self.BG, fg=self.TEXT_DIM,
                 font=("Arial", 9)).pack(side="left")

        # --- Разделитель ---
        tk.Frame(form, bg=self.BORDER, height=1).pack(fill="x", pady=15)

        # --- Чекбоксы ---
        self.var_close = tk.BooleanVar(value=bool(self.cfg.get("close_after_launch", False)))
        ttk.Checkbutton(form, text="Закрывать лаунчер после запуска игры",
                        variable=self.var_close,
                        style="Dark.TCheckbutton").pack(anchor="w", pady=4)

        self.var_auto = tk.BooleanVar(value=bool(self.cfg.get("auto_check_updates", True)))
        ttk.Checkbutton(form, text="Проверять обновления при запуске",
                        variable=self.var_auto,
                        style="Dark.TCheckbutton").pack(anchor="w", pady=4)

        # --- Кнопки внизу ---
        btn_row = tk.Frame(outer, bg=self.BG)
        btn_row.pack(fill="x", side="bottom", pady=(25, 0))

        ttk.Button(btn_row, text="Сбросить",
                   style="Dark.TButton",
                   command=self._reset).pack(side="left")

        ttk.Button(btn_row, text="Сохранить",
                   style="Accent.TButton",
                   command=self._save).pack(side="right")

        # Статус сохранения
        self.status_label = tk.Label(btn_row, text="", bg=self.BG, fg=self.ACCENT,
                                     font=("Arial", 9, "italic"))
        self.status_label.pack(side="right", padx=15)

    def _add_label(self, parent, text):
        tk.Label(parent, text=text, bg=self.BG, fg=self.TEXT,
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 4))

    # ------------------------------------------------------------------
    # Обработчики
    # ------------------------------------------------------------------
    def _browse_dir(self):
        p = filedialog.askdirectory(
            title="Выберите папку .minecraft",
            initialdir=self.var_dir.get() or "."
        )
        if p:
            self.var_dir.set(p)

    def _browse_java(self):
        p = filedialog.askopenfilename(
            title="Выберите java.exe",
            filetypes=[("java.exe", "java.exe"), ("Все файлы", "*.*")]
        )
        if p:
            self.var_java.set(p)

    def _save(self):
        try:
            ram = int(self.var_ram.get())
        except (ValueError, tk.TclError):
            ram = 4096

        self.cfg["username"] = self.var_name.get().strip() or "Player"
        self.cfg["server_name"] = self.var_server.get().strip() or "MY SERVER"
        self.cfg["game_directory"] = self.var_dir.get().strip()
        self.cfg["java_path"] = self.var_java.get().strip()
        self.cfg["ram_mb"] = ram
        self.cfg["close_after_launch"] = bool(self.var_close.get())
        self.cfg["auto_check_updates"] = bool(self.var_auto.get())

        # Колбэк наружу
        self.on_save(self.cfg)

        # Показываем статус
        self.status_label.config(text="✓ Сохранено")
        self.after(2000, lambda: self.status_label.config(text=""))

    def _reset(self):
        """Сброс полей к значениям по умолчанию."""
        self.var_name.set("Player")
        self.var_server.set("MY SERVER")
        self.var_dir.set("")
        self.var_java.set("")
        self.var_ram.set(4096)
        self.var_close.set(False)
        self.var_auto.set(True)
        self.status_label.config(text="Сброшено (не сохранено)", fg=self.TEXT_DIM)
        self.after(2000, lambda: self.status_label.config(text="", fg=self.ACCENT))