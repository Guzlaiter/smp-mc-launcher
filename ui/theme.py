"""
Единое место для цветов, шрифтов, размеров и ttk-стилей.
Больше никаких копий палитры в каждом файле — правим тут.
"""
import tkinter as tk
from pathlib import Path
from tkinter import ttk

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"


class C:
    """Цвета."""
    WINDOW       = "#1e1e1e"
    TITLEBAR     = "#111111"
    TITLEBAR_FG  = "#888888"
    SIDEBAR      = "#1a1a1a"
    BG           = "#2b2b2b"
    PANEL        = "#1f1f1f"
    PANEL_ALT    = "#252525"
    BORDER       = "#3a3a3a"

    ACCENT       = "#8B5A2B"
    ACCENT_HOV   = "#A56A35"

    TEXT         = "#e0e0e0"
    TEXT_DIM     = "#888888"

    # текст поверх кнопок-плашек
    BTN_TEXT        = "#f8e6c8"
    BTN_TEXT_ACTIVE = "#ffffff"
    TEXT_SHADOW     = "#2a1608"

    # цвета статуса по уровням
    LEVELS = {
        "info":  "#e7d3a7",
        "ok":    "#8ee08e",
        "warn":  "#f0b040",
        "error": "#e5604f",
    }


class F:
    """Шрифты (кортежи — их можно создавать до появления окна)."""
    TEXT    = ("Arial", 10)
    BOLD    = ("Arial", 10, "bold")
    SMALL   = ("Arial", 9)
    SMALL_B = ("Arial", 9, "bold")
    TINY    = ("Arial", 8)
    H1      = ("Arial", 18, "bold")
    H2      = ("Arial", 13, "bold")
    TAB     = ("Arial", 11, "bold")


class Size:
    """Размеры интерфейса."""
    WINDOW       = (1000, 650)
    TITLEBAR_H   = 34
    TITLE_BTN    = (32, 34)     # холст под иконку в заголовке
    TITLE_ICON   = (22, 22)     # сама иконка
    SIDEBAR_W    = 200
    STATUSBAR_H  = 38
    TAB          = (184, 47)    # кнопка-вкладка в сайдбаре
    EXIT         = (150, 39)


def apply_ttk_theme(widget: tk.Misc) -> None:
    """Тёмная тема для ttk-виджетов (Entry, Spinbox, Checkbutton, Button)."""
    style = ttk.Style(widget)
    try:
        style.theme_use("clam")  # позволяет красить виджеты
    except tk.TclError:
        pass

    field = dict(
        fieldbackground=C.PANEL, background=C.PANEL, foreground=C.TEXT,
        bordercolor=C.BORDER, lightcolor=C.BORDER, darkcolor=C.BORDER,
        relief="flat",
    )
    style.configure("Dark.TEntry", insertcolor=C.TEXT, **field)
    style.map("Dark.TEntry",
              fieldbackground=[("focus", C.PANEL_ALT)],
              bordercolor=[("focus", C.ACCENT)])

    style.configure("Dark.TSpinbox", arrowcolor=C.TEXT, insertcolor=C.TEXT,
                    padding=(4, 5), **field)
    style.map("Dark.TSpinbox",
              fieldbackground=[("focus", C.PANEL_ALT)],
              bordercolor=[("focus", C.ACCENT)])

    style.configure("Dark.TCheckbutton",
                    background=C.BG, foreground=C.TEXT,
                    focuscolor=C.BG, indicatorcolor=C.PANEL)
    style.map("Dark.TCheckbutton",
              background=[("active", C.BG)],
              foreground=[("active", C.ACCENT_HOV)],
              indicatorcolor=[("selected", C.ACCENT), ("active", C.ACCENT)])

    style.configure("Dark.TButton",
                    background=C.BORDER, foreground=C.TEXT,
                    bordercolor=C.BORDER, lightcolor=C.BORDER, darkcolor=C.BORDER,
                    relief="flat", padding=(12, 6))
    style.map("Dark.TButton",
              background=[("active", "#4a4a4a"), ("disabled", "#2e2e2e")],
              foreground=[("disabled", C.TEXT_DIM)])

    style.configure("Accent.TButton",
                    background=C.ACCENT, foreground="white",
                    bordercolor=C.ACCENT, lightcolor=C.ACCENT, darkcolor=C.ACCENT,
                    relief="flat", padding=(14, 6), font=F.BOLD)
    style.map("Accent.TButton",
              background=[("active", C.ACCENT_HOV)],
              foreground=[("active", "white")])
