import tkinter as tk
from tkinter import ttk, filedialog


class SettingsDialog(tk.Toplevel):
    def __init__(self, master, cfg: dict, on_save):
        super().__init__(master)
        self.title("Настройки")
        self.cfg = dict(cfg)
        self.on_save = on_save
        self.resizable(False, False)
        self.grab_set()

        f = ttk.Frame(self, padding=15)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Ник в игре:").pack(anchor="w")
        self.var_name = tk.StringVar(value=self.cfg.get("username", "Player"))
        ttk.Entry(f, textvariable=self.var_name, width=50).pack(fill="x", pady=(0, 10))

        ttk.Label(f, text="Название в окне:").pack(anchor="w")
        self.var_server = tk.StringVar(value=self.cfg.get("server_name", "MY SERVER"))
        ttk.Entry(f, textvariable=self.var_server).pack(fill="x", pady=(0, 10))

        ttk.Label(f, text="Папка игры:").pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(0, 10))
        self.var_dir = tk.StringVar(value=self.cfg["game_directory"])
        ttk.Entry(row, textvariable=self.var_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="...", width=3, command=self._browse_dir).pack(side="left", padx=(5, 0))

        ttk.Label(f, text="Java (пусто = автоопределение):").pack(anchor="w")
        row2 = ttk.Frame(f)
        row2.pack(fill="x", pady=(0, 10))
        self.var_java = tk.StringVar(value=self.cfg.get("java_path", ""))
        ttk.Entry(row2, textvariable=self.var_java).pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="...", width=3, command=self._browse_java).pack(side="left", padx=(5, 0))

        ttk.Label(f, text="Выделяемая RAM (MB):").pack(anchor="w")
        self.var_ram = tk.IntVar(value=int(self.cfg.get("ram_mb", 4096)))
        ttk.Spinbox(f, from_=1024, to=32768, increment=512,
                    textvariable=self.var_ram).pack(fill="x", pady=(0, 10))

        self.var_close = tk.BooleanVar(value=bool(self.cfg.get("close_after_launch", False)))
        ttk.Checkbutton(f, text="Закрывать лаунчер после запуска",
                        variable=self.var_close).pack(anchor="w", pady=(0, 5))

        self.var_auto = tk.BooleanVar(value=bool(self.cfg.get("auto_check_updates", True)))
        ttk.Checkbutton(f, text="Проверять обновления при запуске",
                        variable=self.var_auto).pack(anchor="w", pady=(0, 10))

        btns = ttk.Frame(f)
        btns.pack(fill="x")
        ttk.Button(btns, text="Сохранить", command=self._save).pack(side="right")
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side="right", padx=5)

    def _browse_dir(self):
        p = filedialog.askdirectory(initialdir=self.var_dir.get() or ".")
        if p:
            self.var_dir.set(p)

    def _browse_java(self):
        p = filedialog.askopenfilename(
            title="java.exe",
            filetypes=[("java.exe", "java.exe"), ("Все файлы", "*.*")],
        )
        if p:
            self.var_java.set(p)

    def _save(self):
        self.cfg["username"] = self.var_name.get().strip() or "Player"
        self.cfg["server_name"] = self.var_server.get().strip() or "MY SERVER"
        self.cfg["game_directory"] = self.var_dir.get().strip()
        self.cfg["java_path"] = self.var_java.get().strip()
        self.cfg["ram_mb"] = int(self.var_ram.get())
        self.cfg["close_after_launch"] = bool(self.var_close.get())
        self.cfg["auto_check_updates"] = bool(self.var_auto.get())
        self.on_save(self.cfg)
        self.destroy()