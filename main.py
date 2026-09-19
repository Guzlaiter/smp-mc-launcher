import sys
from tkinter import messagebox

from app.config import load_config
from app.utils import log
from ui.main_window import MainWindow
from ui.widgets import CustomWindow


class LauncherApp(CustomWindow):
    def __init__(self):
        super().__init__(title="Create SMP — Launcher")
        MainWindow(self, load_config())


def main():
    try:
        LauncherApp().mainloop()
    except Exception as e:
        log.exception("fatal")
        try:
            messagebox.showerror("Ошибка", f"Критическая ошибка: {e}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
