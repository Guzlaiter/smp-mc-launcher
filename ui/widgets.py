"""
Базовые виджеты:
  ImageButton   — кнопка из картинок, рисуется на любом canvas (можно прямо поверх фона);
  ButtonWidget  — то же самое, но со своим маленьким canvas (для pack/grid);
  CustomWindow  — окно без системной рамки со своим заголовком.
"""
import ctypes
import sys
import tkinter as tk
from typing import Callable, Optional

from ui.assets import Assets
from ui.theme import ASSETS_DIR, C, F, Size, apply_ttk_theme


class ImageButton:
    """
    Состояния: normal / hover / pressed / active (выбранная вкладка) / disabled.
    states — словарь картинок из Assets.button_states(); пустой -> плоская запасная кнопка.
    x, y — ЦЕНТР кнопки на canvas.
    """

    def __init__(self, canvas: tk.Canvas, x: float, y: float, states: dict, *,
                 size: tuple[int, int], text: str = "", font=F.TAB,
                 fg: str = C.BTN_TEXT, fg_active: str = C.BTN_TEXT_ACTIVE,
                 command: Optional[Callable[[], None]] = None):
        self.canvas = canvas
        self.states = states or {}
        self.w, self.h = size
        self.command = command
        self.fg, self.fg_active = fg, fg_active
        self.x, self.y = x, y

        self._hover = self._down = self._active = False
        self._enabled = True

        self._tag = f"imgbtn_{id(self)}"
        tags = (self._tag,)
        self._rect = None
        if not self.states:  # запасной вариант, если нет картинок
            self._rect = canvas.create_rectangle(0, 0, 0, 0, outline=C.BORDER, tags=tags)
        self._img = canvas.create_image(x, y, anchor="center", tags=tags)
        self._shadow = canvas.create_text(x + 1, y + 1, text=text, font=font,
                                          fill=C.TEXT_SHADOW, tags=tags)
        self._label = canvas.create_text(x, y, text=text, font=font, fill=fg, tags=tags)

        for ev, fn in (("<Enter>", self._on_enter), ("<Leave>", self._on_leave),
                       ("<ButtonPress-1>", self._on_press),
                       ("<ButtonRelease-1>", self._on_release)):
            canvas.tag_bind(self._tag, ev, fn)
        self._render()

    # --- публичное ---------------------------------------------------
    def set_active(self, active: bool) -> None:
        self._active = active
        self._render()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._hover = self._down = False
        self._render()

    def set_text(self, text: str) -> None:
        self.canvas.itemconfigure(self._label, text=text)
        self.canvas.itemconfigure(self._shadow, text=text)

    def move(self, x: float, y: float) -> None:
        """Переместить центр кнопки (для раскладки при ресайзе)."""
        self.x, self.y = x, y
        self._render()

    # --- внутреннее --------------------------------------------------
    def _state(self) -> str:
        if not self._enabled:
            return "disabled"
        if self._down:
            return "pressed"
        if self._active:
            return "active"
        if self._hover:
            return "hover"
        return "normal"

    def _render(self) -> None:
        c, st = self.canvas, self._state()
        dy = 1 if st == "pressed" else 0
        x, y = self.x, self.y + dy

        img = self.states.get(st) or self.states.get("normal")
        if img is not None:
            c.itemconfigure(self._img, image=img)
        if self._rect is not None:
            fill = {"normal": C.ACCENT, "hover": C.ACCENT_HOV, "active": "#5a3a1b",
                    "pressed": "#5a3a1b", "disabled": "#444444"}[st]
            c.coords(self._rect, x - self.w / 2, y - self.h / 2,
                     x + self.w / 2, y + self.h / 2)
            c.itemconfigure(self._rect, fill=fill)

        c.coords(self._img, x, y)
        c.coords(self._shadow, x + 1, y + 2)
        c.coords(self._label, x, y + 1)
        color = C.TEXT_DIM if st == "disabled" else (
            self.fg_active if st in ("pressed", "active") else self.fg)
        c.itemconfigure(self._label, fill=color)

    def _on_enter(self, _e):
        if self._enabled:
            self._hover = True
            self.canvas.configure(cursor="hand2")
            self._render()

    def _on_leave(self, _e):
        self._hover = self._down = False
        self.canvas.configure(cursor="")
        self._render()

    def _on_press(self, _e):
        if self._enabled:
            self._down = True
            self._render()

    def _on_release(self, _e):
        was_down = self._down
        self._down = False
        self._render()
        if was_down and self._enabled and self.command:
            self.command()


class ButtonWidget(tk.Canvas):
    """ImageButton со своим canvas — можно класть через pack/grid."""

    def __init__(self, master, states: dict, size: tuple[int, int], *,
                 bg: str, **button_kw):
        super().__init__(master, width=size[0], height=size[1], bg=bg,
                         highlightthickness=0, bd=0)
        self.button = ImageButton(self, size[0] / 2, size[1] / 2, states,
                                  size=size, **button_kw)

    def set_active(self, active: bool) -> None:
        self.button.set_active(active)

    def set_enabled(self, enabled: bool) -> None:
        self.button.set_enabled(enabled)

    def set_text(self, text: str) -> None:
        self.button.set_text(text)


class CustomWindow(tk.Tk):
    """
    Окно без системной рамки: заголовок, перетаскивание, свернуть/закрыть.
    Внутри self.content — контейнер под MainWindow.
    """

    def __init__(self, title: str = "Launcher", size=Size.WINDOW):
        super().__init__()
        self.title(title)
        self.configure(bg=C.WINDOW)
        self.overrideredirect(False)

        self.assets = Assets(ASSETS_DIR)
        self._drag = None
        self._minimized = False

        w, h = size
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        apply_ttk_theme(self)
        self._build_titlebar(title)
        self.content = tk.Frame(self, bg=C.BG)
        self.content.pack(side="top", fill="both", expand=True)

        self._setup_icons()
        self.bind("<Map>", self._on_map)
        self.after(300, self._fix_taskbar_icon)

    # ------------------------------------------------------------------
    # Заголовок
    # ------------------------------------------------------------------
    def _build_titlebar(self, title: str) -> None:
        self.titlebar = tk.Frame(self, bg=C.TITLEBAR, height=Size.TITLEBAR_H)
        # self.titlebar.pack(side="top", fill="x")
        # self.titlebar.pack_propagate(False)

        # self.title_label = tk.Label(self.titlebar, text=title, bg=C.TITLEBAR,
        #                             fg=C.TITLEBAR_FG, font=F.SMALL)
        # self.title_label.pack(side="left", padx=12)

        # for w in (self.titlebar, self.title_label):
        #     w.bind("<ButtonPress-1>", self._start_drag)
        #     w.bind("<ButtonRelease-1>", self._stop_drag)
        #     w.bind("<B1-Motion>", self._do_drag)

        # # справа налево: закрыть, свернуть (остальные добавляются через add_titlebar_button)
        # self.add_titlebar_button("close.png", "close_press.png", self._on_close)
        # # self.add_titlebar_button("minimize.png", "minimize_press.png", self.minimize)

    def add_titlebar_button(self, icon: str, icon_pressed: str,
                            command: Callable[[], None]) -> ButtonWidget:
        """Иконка-кнопка в заголовке; каждая следующая встаёт левее предыдущей."""
        states = self.assets.button_states(icon, pressed=icon_pressed,
                                           size=Size.TITLE_ICON)
        btn = ButtonWidget(self.titlebar, states, Size.TITLE_BTN,
                           bg=C.TITLEBAR, command=command)
        btn.pack(side="right", padx=(0, 4))
        return btn

    def set_title_text(self, text: str) -> None:
        self.title_label.config(text=text)
        self.title(text)

    # ------------------------------------------------------------------
    # Иконки / панель задач
    # ------------------------------------------------------------------
    def _setup_icons(self) -> None:
        try:
            self.iconphoto(True, tk.PhotoImage(file=str(ASSETS_DIR / "logo.png")))
        except Exception:
            pass
        try:
            self.iconbitmap(str(ASSETS_DIR / "logo.ico"))
        except Exception:
            pass

    def _fix_taskbar_icon(self) -> None:
        """Возвращает окно в панель задач Windows (overrideredirect его оттуда убирает)."""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.winfo_id()) or self.winfo_id()
            GWL_EXSTYLE, WS_EX_APPWINDOW, WS_EX_TOOLWINDOW = -20, 0x00040000, 0x00000080
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex = (ex & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)  # NOMOVE|NOSIZE|NOZORDER|FRAMECHANGED
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Свернуть (с overrideredirect обычный iconify не работает)
    # ------------------------------------------------------------------
    def minimize(self) -> None:
        self._minimized = True
        self.update_idletasks()
        self.overrideredirect(False)
        self.iconify()

    def _on_map(self, event) -> None:
        if event.widget is self and self._minimized:
            self._minimized = False
            self.update_idletasks()
            self.overrideredirect(False)
            self.state("normal")
            self.after(50, self._fix_taskbar_icon)

    # ------------------------------------------------------------------
    # Перетаскивание
    # ------------------------------------------------------------------
    def _start_drag(self, e) -> None:
        self._drag = (e.x_root - self.winfo_x(), e.y_root - self.winfo_y())

    def _stop_drag(self, _e) -> None:
        self._drag = None

    def _do_drag(self, e) -> None:
        if self._drag:
            self.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    # ------------------------------------------------------------------
    def _on_close(self) -> None:
        self.destroy()
        sys.exit(0)
