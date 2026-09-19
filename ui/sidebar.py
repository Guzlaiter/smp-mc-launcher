"""Боковая панель: логотип, вкладки-плашки, кнопка «Выход»."""
import tkinter as tk
from typing import Callable

from ui.assets import Assets
from ui.theme import C, F, Size
from ui.widgets import ButtonWidget


class Sidebar(tk.Frame):
    def __init__(self, master, assets: Assets, tabs: list[tuple[str, str]],
                 on_select: Callable[[str], None], on_exit: Callable[[], None]):
        """tabs — список (key, заголовок)."""
        super().__init__(master, bg=C.SIDEBAR, width=Size.SIDEBAR_W)
        self.pack_propagate(False)
        self._buttons: dict[str, ButtonWidget] = {}

        # Выход — прижат к низу (пакуем первым, чтобы не выдавило)
        exit_states = assets.button_states("exit.png", size=Size.EXIT)
        ButtonWidget(self, exit_states, Size.EXIT, bg=C.SIDEBAR, text="ВЫХОД",
                     font=F.SMALL_B, command=on_exit).pack(side="bottom", pady=16)

        # Логотип
        logo = assets.photo("logo.png", width=170)
        if logo is not None:
            tk.Label(self, image=logo, bg=C.SIDEBAR).pack(pady=(18, 22))
        else:
            tk.Label(self, text="CREATE\nSMP", font=("Impact", 24), bg=C.SIDEBAR,
                     fg=C.ACCENT, justify="center").pack(pady=(18, 22))

        # Вкладки
        states = assets.button_states("btn.png", pressed="btn_press.png", size=Size.TAB)
        for key, title in tabs:
            btn = ButtonWidget(self, states, Size.TAB, bg=C.SIDEBAR, text=title,
                               font=F.TAB, command=lambda k=key: on_select(k))
            btn.pack(pady=3)
            self._buttons[key] = btn

    def set_active(self, key: str) -> None:
        for k, btn in self._buttons.items():
            btn.set_active(k == key)
