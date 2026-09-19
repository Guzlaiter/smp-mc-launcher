"""
ВКЛАДКА-ПУСТЫШКА — заготовка для новых разделов (моды, скриншоты, новости и т.д.).

Как добавить свою вкладку:
  1. Скопируйте этот файл, переименуйте класс, задайте key и title.
  2. Наполните build() своими виджетами.
  3. Добавьте класс в список PAGES в ui/pages/__init__.py.
Кнопка в сайдбаре и переключение появятся сами.
"""
import tkinter as tk

from ui.pages.base import BasePage
from ui.theme import C, F


class BlankPage(BasePage):
    key = "blank"
    title = "Пустышка"

    def build(self) -> None:
        card = tk.Frame(self, bg=C.PANEL, bd=1, relief="solid", padx=40, pady=30)
        card.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(card, text=self.title.upper(), bg=C.PANEL, fg=C.ACCENT,
                 font=F.H1).pack()
        tk.Frame(card, bg=C.ACCENT, height=2).pack(fill="x", pady=(8, 14))
        tk.Label(card, text="Раздел в разработке", bg=C.PANEL, fg=C.TEXT_DIM,
                 font=F.TEXT).pack()

    def on_show(self) -> None:
        # сюда — то, что надо обновить при каждом открытии вкладки
        pass
