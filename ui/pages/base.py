"""Базовый класс вкладки и общий контекст, который получает каждая страница."""
import tkinter as tk
from dataclasses import dataclass
from typing import Callable

from app.controller import LauncherController
from ui.assets import Assets
from ui.theme import C


@dataclass
class PageContext:
    assets: Assets
    controller: LauncherController
    navigate: Callable[[str], None]          # navigate("settings")
    save_config: Callable[[dict], None]      # сохранить конфиг и применить (заголовок окна и т.п.)


class BasePage(tk.Frame):
    """
    Вкладка. Наследуйтесь, задайте key и title, переопределите build().

      key   — уникальный id (для navigate и сайдбара)
      title — текст на кнопке вкладки
    """
    key: str = ""
    title: str = ""

    def __init__(self, master, ctx: PageContext):
        super().__init__(master, bg=C.BG)
        self.ctx = ctx
        self.build()

    # --- переопределять ---------------------------------------------
    def build(self) -> None:
        """Создать виджеты (вызывается один раз)."""

    def on_show(self) -> None:
        """Вкладка стала видимой (обновить данные)."""

    def on_hide(self) -> None:
        """Вкладку закрыли."""

    def on_busy(self, busy: bool) -> None:
        """Началась/закончилась фоновая операция (обновление, запуск игры)."""
