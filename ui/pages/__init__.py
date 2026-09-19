"""
Реестр вкладок. Порядок в списке = порядок кнопок в сайдбаре.
Новая вкладка = новый класс (см. blank.py) + одна строка здесь.
"""
from ui.pages.blank import BlankPage
from ui.pages.home import HomePage
from ui.pages.settings import SettingsPage

PAGES = [HomePage, SettingsPage]

__all__ = ["PAGES", "HomePage", "SettingsPage", "BlankPage"]
