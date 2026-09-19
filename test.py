# main.py
import tkinter as tk
from tkinter import font as tkfont
import sys
import ctypes

from ui.settings import SettingsTab   # <-- наш модуль


class CreateMechanicaLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Create Launcher")
        self.root.geometry("1100x700")
        self.root.configure(bg="#1e1e1e")

        # --- Конфиг (в реальном проекте — из json-файла) ---
        self.cfg = {
            "username": "Player",
            "server_name": "MY SERVER",
            "game_directory": "",
            "java_path": "",
            "ram_mb": 4096,
            "close_after_launch": False,
            "auto_check_updates": True,
        }

        # Иконка
        try:
            self.icon_png = tk.PhotoImage(file="assets/logo.png")
            self.root.iconphoto(True, self.icon_png)
        except Exception as e:
            print(f"[Icon] {e}")

        self.root.overrideredirect(True)
        self.root.after(300, self.fix_taskbar_icon)

        self.x_offset = 0
        self.y_offset = 0

        # Цвета
        self.bg_color = "#2b2b2b"
        self.sidebar_color = "#1a1a1a"
        self.accent_color = "#8B5A2B"
        self.text_color = "#e0e0e0"
        self.button_green = "#4CAF50"

        self.header_font = tkfont.Font(family="Arial", size=14, weight="bold")
        self.normal_font = tkfont.Font(family="Arial", size=10)
        self.small_font = tkfont.Font(family="Arial", size=9)
        self.control_font = tkfont.Font(family="Arial", size=12, weight="bold")

        self.create_layout()

    def fix_taskbar_icon(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            ex = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ex = (ex & ~0x00000080) | 0x00040000
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)
        except Exception as e:
            print(f"[Taskbar] {e}")

    def close_app(self):
        self.root.destroy()
        sys.exit(0)

    def start_move(self, event):
        self.x_offset = event.x
        self.y_offset = event.y

    def stop_move(self, event):
        self.x_offset = None

    def do_move(self, event):
        x = self.root.winfo_pointerx() - self.x_offset
        y = self.root.winfo_pointery() - self.y_offset
        self.root.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Переключение вкладок
    # ------------------------------------------------------------------
    def show_home(self):
        self.settings_tab.pack_forget()
        self.home_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def show_settings(self):
        self.home_frame.pack_forget()
        self.settings_tab.pack(fill="both", expand=True, padx=20, pady=20)

    def on_settings_save(self, new_cfg: dict):
        """Колбэк, вызывается при сохранении настроек."""
        self.cfg = new_cfg
        print("Настройки сохранены:", self.cfg)
        # Здесь можно сохранить конфиг в JSON-файл
        # import json
        # with open("config.json", "w", encoding="utf-8") as f:
        #     json.dump(self.cfg, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    def create_layout(self):
        # --- Верхняя панель ---
        title_bar = tk.Frame(self.root, bg="#111111", height=30)
        title_bar.pack(side="top", fill="x")
        title_bar.bind("<ButtonPress-1>", self.start_move)
        title_bar.bind("<ButtonRelease-1>", self.stop_move)
        title_bar.bind("<B1-Motion>", self.do_move)

        tk.Label(title_bar, text="Create Launcher", bg="#111111", fg="#888888",
                 font=self.small_font).pack(side="left", padx=10)

        btn_close = tk.Button(title_bar, text="✕", bg="#111111", fg="white", bd=0,
                              font=self.control_font, command=self.close_app, padx=15)
        btn_close.pack(side="right", fill="y")
        btn_close.bind("<Enter>", lambda e: btn_close.config(bg="#c42b1c"))
        btn_close.bind("<Leave>", lambda e: btn_close.config(bg="#111111"))

        # --- Боковая панель ---
        sidebar = tk.Frame(self.root, bg=self.sidebar_color, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        try:
            original_logo = tk.PhotoImage(file="assets/logo.png")
            w = original_logo.width()
            factor = max(1, w // 160)
            self.logo_image = original_logo.subsample(factor, factor)
            tk.Label(sidebar, image=self.logo_image, bg=self.sidebar_color).pack(pady=20)
        except Exception as e:
            print(f"[Logo] {e}")
            tk.Label(sidebar, text="CREATE\nMECHANICA", font=("Impact", 24),
                     bg=self.sidebar_color, fg=self.accent_color,
                     justify="center").pack(pady=20)

        # Кнопки меню — теперь с командами
        self._make_menu_button(sidebar, "Главная",         self.show_home)
        self._make_menu_button(sidebar, "Обновления [1 NEW]", lambda: None)
        self._make_menu_button(sidebar, "Моды\n45 активных",  lambda: None)
        self._make_menu_button(sidebar, "Настройки",       self.show_settings)  # <--

        # --- Контейнер для вкладок ---
        self.content_container = tk.Frame(self.root, bg=self.bg_color)
        self.content_container.pack(side="top", fill="both", expand=True)

        # ===== Главная вкладка =====
        self.home_frame = tk.Frame(self.content_container, bg=self.bg_color)

        left_area = tk.Frame(self.home_frame, bg=self.bg_color)
        left_area.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        image_placeholder = tk.Frame(left_area, bg="#3a3a3a")
        image_placeholder.pack(fill="both", expand=True)
        tk.Label(image_placeholder, text="[Скриншот игры / Фон]\nMega Gantry Cranes",
                 bg="#3a3a3a", fg="#666", font=("Arial", 20)
                 ).place(relx=0.5, rely=0.5, anchor="center")

        bottom = tk.Frame(left_area, bg=self.bg_color)
        bottom.pack(fill="x", pady=10)

        play_frame = tk.Frame(bottom, bg=self.bg_color)
        play_frame.pack(side="left", anchor="sw", padx=(0, 20), pady=20)
        tk.Button(play_frame, text="PLAY", font=("Arial", 30, "bold"),
                  bg=self.button_green, fg="white", bd=0, padx=60, pady=15,
                  activebackground="#45a049", cursor="hand2").pack()
        tk.Label(play_frame, text="Forge 47.3.1 | MC 1.20.1",
                 bg=self.bg_color, fg="gray").pack(pady=5)

        # ===== Вкладка настроек (наш модуль!) =====
        self.settings_tab = SettingsTab(
            self.content_container,
            cfg=self.cfg,
            on_save=self.on_settings_save,
        )

        # Показываем главную по умолчанию
        self.show_home()

    def _make_menu_button(self, parent, text, command):
        btn = tk.Button(parent, text=text, font=self.normal_font,
                        bg=self.sidebar_color, fg=self.text_color,
                        bd=0, anchor="w", padx=20, pady=10,
                        activebackground=self.accent_color, activeforeground="white",
                        command=command)
        btn.pack(fill="x")


if __name__ == "__main__":
    root = tk.Tk()
    app = CreateMechanicaLauncher(root)
    root.mainloop()