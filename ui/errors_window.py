"""Окно проверок перед запуском — в стиле основного приложения."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui.theme import C, F, apply_ttk_theme
from app.utils import log

# Размеры окна
WIN_W = 560
WIN_MIN_H = 260
WIN_MAX_H = 560

# Сколько пикселей занимает «обвязка» (заголовок + подзаголовок + нижняя
# панель + внутренние отступы), не считая списка проверок. Нужно, чтобы
# из WIN_MAX_H получить максимум для высоты списка.
_CHROME_H = 200


# ---------------------------------------------------------------------------
# Строка проверки
# ---------------------------------------------------------------------------
class CheckRow(tk.Frame):
    """Одна строка отчёта: ✓/✗  Имя  [ сообщение об ошибке ]."""

    def __init__(self, parent, name: str, result, message: str = "",
                 ok_icon: str = "✓", fail_icon: str = "✗"):
        super().__init__(parent, bg=C.PANEL)

        success = result is not False and result is not None and result != ""
        color = C.LEVELS["ok" if success else "error"]

        tk.Frame(self, bg=color, width=3).pack(side="left", fill="y")

        tk.Label(self, text=(ok_icon if success else fail_icon),
                 bg=C.PANEL, fg=color, font=F.H2, width=3
                 ).pack(side="left", padx=(10, 0))

        tk.Label(self, text=name, bg=C.PANEL, fg=C.TEXT, font=F.TEXT,
                 anchor="w").pack(side="left", padx=(4, 10), fill="x", expand=True)

        if not success:
            text = message or (result if isinstance(result, str) else "")
            if text:
                tk.Label(self, text=text, bg=C.PANEL, fg=C.TEXT_DIM,
                         font=F.SMALL, anchor="e", justify="right",
                         wraplength=280
                         ).pack(side="right", padx=(10, 12))


# ---------------------------------------------------------------------------
# Само окно
# ---------------------------------------------------------------------------
class StartupChecksWindow(tk.Toplevel):
    def __init__(self, parent, checks):
        super().__init__(parent)

        self.withdraw()                      # строим скрыто
        self.title("Проверка запуска")
        self.configure(bg=C.BG)
        self.resizable(False, False)

        self.checks = list(checks)
        self._has_error = any(
            result is False or result is None or result == ""
            for _, result, _ in self.checks
        )

        log.info("Проверка запуска: %d проверок, ошибок: %s",
                 len(self.checks), self._has_error)
        for name, result, message in self.checks:
            if result is False or result is None or result == "":
                log.warning("Проверка не пройдена: %s — %s", name, message)
            else:
                log.info("Проверка OK: %s — %s", name, result)

        apply_ttk_theme(self)
        self._build_ui()

        # показываем, когда Tk уже разложил виджеты
        self.after_idle(self._show)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=C.BG)
        outer.pack(fill="both", expand=True, padx=24, pady=20)

        # --- заголовок ---------------------------------------------------
        head = tk.Frame(outer, bg=C.BG)
        head.pack(fill="x")
        tk.Label(head, text="ПРОВЕРКА ЗАПУСКА", bg=C.BG, fg=C.ACCENT,
                 font=F.H1).pack(anchor="w")
        tk.Frame(outer, bg=C.ACCENT, height=2).pack(fill="x", pady=(4, 4))

        subtitle = ("Обнаружены проблемы. Устраните их и запустите лаунчер снова."
                    if self._has_error else "Все проверки пройдены.")
        tk.Label(outer, text=subtitle, bg=C.BG, fg=C.TEXT_DIM,
                 font=F.SMALL).pack(anchor="w", pady=(0, 12))

        # --- область со скроллом -----------------------------------------
        area = tk.Frame(outer, bg=C.BG)
        area.pack(fill="x")                       # высота по содержимому

        self.canvas = tk.Canvas(area, bg=C.BG, highlightthickness=0, bd=0,
                                height=WIN_MIN_H - _CHROME_H)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scroll = ttk.Scrollbar(area, orient="vertical",
                                    command=self.canvas.yview)
        self.scroll.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scroll.set)

        inner = tk.Frame(self.canvas, bg=C.BG)
        self._inner = inner
        self._inner_id = self.canvas.create_window((0, 0), window=inner,
                                                   anchor="nw")

        # карточки проверок
        for i, (name, result, message) in enumerate(self.checks):
            card = tk.Frame(inner, bg=C.PANEL)
            card.pack(fill="x", pady=(0 if i == 0 else 6, 0))
            CheckRow(card, name, result, message).pack(fill="x", padx=1, pady=1)

        inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._bind_mousewheel(self.canvas)

        # --- нижняя панель ----------------------------------------------
        bar = tk.Frame(outer, bg=C.BG)
        bar.pack(fill="x", pady=(16, 0))

        label = "Закрыть" if self._has_error else "Продолжить"
        style = "Accent.TButton" if self._has_error else "Dark.TButton"
        ttk.Button(bar, text=label, style=style,
                   command=self.destroy).pack(side="right")

        # --- фиксируем высоту канваса под содержимое ---------------------
        # Canvas по умолчанию не тянется под inner — делаем это руками.
        self.update_idletasks()
        self._sync_canvas_height()

    # ------------------------------------------------------------------
    def _sync_canvas_height(self) -> None:
        """Canvas = высота списка, но не больше, чем позволяет окно."""
        need = self._inner.winfo_reqheight()
        max_list_h = max(80, WIN_MAX_H - _CHROME_H)
        h = max(80, min(need, max_list_h))
        self.canvas.configure(height=h)

    def _on_inner_configure(self, _event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._sync_canvas_height()

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self._inner_id, width=event.width)

    # ------------------------------------------------------------------
    def _show(self) -> None:
        # transient — только если родитель реально видим
        try:
            if isinstance(self.master, (tk.Tk, tk.Toplevel)) and self.master.winfo_viewable():
                self.transient(self.master)
        except tk.TclError:
            pass

        # Layout точно пересчитан; считаем размеры ЯВНО, не через winfo_width/height
        self.update_idletasks()

        w = WIN_W
        h = max(WIN_MIN_H, min(WIN_MAX_H, self.winfo_reqheight()))

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)

        self.geometry(f"{w}x{h}+{x}+{y}")

        self.deiconify()
        self.lift()
        try:
            self.focus_force()
        except tk.TclError:
            pass

        # grab — после того, как окно реально на экране
        self.after(50, self._grab)

    def _grab(self) -> None:
        try:
            self.grab_set()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    @staticmethod
    def _bind_mousewheel(widget: tk.Misc) -> None:
        def on_wheel(event):
            if event.delta:
                widget.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        widget.bind_all("<MouseWheel>", on_wheel)          # Windows / macOS
        widget.bind_all("<Button-4>",
                        lambda e: (widget.yview_scroll(-1, "units"), "break")[1])
        widget.bind_all("<Button-5>",
                        lambda e: (widget.yview_scroll(1, "units"), "break")[1])