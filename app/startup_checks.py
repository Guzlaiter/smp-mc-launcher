"""Окно проверок перед запуском — в стиле основного приложения."""
from __future__ import annotations
from ui.errors_window import StartupChecksWindow
from app.startup_check.find_java import find_java

def startup_checks(root):
    checks = [
        (
            "Проверка Java",
            find_java(),
            "Не удалось найти Java. "
            "Установите её или укажите путь в настройках."
        ),
        (
            "[ewe]",
            False,
            "Не удалось найти Java. "
            "Установите её или укажите путь в настройках."
        ),
    ]

    # Есть ли хотя бы одна ошибка
    has_error = any(
        result is False or result is None or result == ""
        for _, result, _ in checks
    )

    if has_error:
        StartupChecksWindow(root, checks)

    return not has_error
