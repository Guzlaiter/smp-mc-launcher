"""Нижняя строка статуса + прогресс. Видна на всех вкладках."""
import tkinter as tk

from ui.theme import C, F, Size


def _one_line(text: str, limit: int = 110) -> str:
    """Статус — одна строка: убираем переводы строк и обрезаем длинные ошибки."""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


class StatusBar(tk.Frame):
    BAR_H = 6

    def __init__(self, master):
        super().__init__(master, bg=C.PANEL, height=Size.STATUSBAR_H)
        self.pack_propagate(False)

        self._label = tk.Label(self, text="Статус: —", bg=C.PANEL,
                               fg=C.LEVELS["info"], font=F.SMALL_B,
                               anchor="w", padx=12)
        self._label.pack(fill="both", expand=True)

        self._bar = tk.Canvas(self, height=self.BAR_H, bg="#241509",
                              highlightthickness=0, bd=0)
        self._bar.pack(fill="x", side="bottom")
        self._fill = self._bar.create_rectangle(0, 0, 0, self.BAR_H,
                                                fill="#c58b3a", outline="")
        self._pct = 0
        self._bar.bind("<Configure>", lambda e: self._redraw())

    def set_status(self, text: str, level: str = "info") -> None:
        self._label.config(text=f"Статус: {_one_line(text)}", fg=C.LEVELS.get(level, C.LEVELS["info"]))

    def set_progress(self, pct: int, text: str = "") -> None:
        self._pct = max(0, min(100, pct))
        self._redraw()
        if text:
            self._label.config(text=f"Статус: {_one_line(text)}")

    def _redraw(self) -> None:
        w = self._bar.winfo_width()
        self._bar.coords(self._fill, 0, 0, w * self._pct / 100, self.BAR_H)
