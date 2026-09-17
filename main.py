import sys
import tkinter as tk
from tkinter import ttk, messagebox

from app.config import load_config
from app.utils import log
from ui.main_window import MainWindow


class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()

        self.title(f"{self.cfg.get('server_name', 'MY SERVER')} — Launcher")
        self.geometry("480x620")
        self.resizable(False, False)

        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        MainWindow(container, self.cfg)


def main():
    try:
        app = LauncherApp()
        app.mainloop()
    except Exception as e:
        log.exception("fatal")
        try:
            messagebox.showerror("Ошибка", f"Критическая ошибка: {e}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()