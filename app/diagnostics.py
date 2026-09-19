"""
Диагностика сети: какие из нужных лаунчеру серверов доступны с этого компьютера.
Любой HTTP-ответ = хост достижим; код показываем для справки (403/451 бывает при блокировках).
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import requests

# (что это, адрес)
HOSTS = [
    ("GitHub — проверка версии сборки",      "https://github.com"),
    ("GitHub codeload — скачивание сборки",  "https://codeload.github.com"),
    ("Modrinth CDN — моды из .mrpack",       "https://cdn.modrinth.com"),
    ("Mojang — список версий",               "https://launchermeta.mojang.com"),
    ("Mojang — библиотеки",                  "https://libraries.minecraft.net"),
    ("Mojang — ресурсы игры",                "https://resources.download.minecraft.net"),
    ("NeoForge — maven",                     "https://maven.neoforged.net"),
]

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 8


@dataclass
class HostResult:
    name: str
    url: str
    ok: bool
    detail: str          # «HTTP 200 · 312 мс» или причина сбоя
    status: int | None = None


def _check(item: tuple[str, str]) -> HostResult:
    name, url = item
    t0 = time.perf_counter()
    try:
        r = requests.get(url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), stream=True,
                         allow_redirects=False,
                         headers={"User-Agent": "MyMinecraftLauncher/1.0"})
        r.close()
        ms = int((time.perf_counter() - t0) * 1000)
        return HostResult(name, url, True, f"HTTP {r.status_code} · {ms} мс", r.status_code)
    except requests.exceptions.ConnectTimeout:
        return HostResult(name, url, False, "таймаут подключения")
    except requests.exceptions.ReadTimeout:
        return HostResult(name, url, False, "сервер не ответил (таймаут)")
    except requests.exceptions.SSLError:
        return HostResult(name, url, False, "ошибка SSL (возможна подмена/блокировка)")
    except requests.exceptions.ConnectionError:
        return HostResult(name, url, False, "нет соединения (DNS/блокировка)")
    except Exception as e:  # noqa: BLE001
        return HostResult(name, url, False, str(e)[:80])


def check_hosts() -> list[HostResult]:
    """Проверяет все хосты параллельно — целиком не дольше ~13 секунд."""
    with ThreadPoolExecutor(max_workers=len(HOSTS)) as pool:
        return list(pool.map(_check, HOSTS))


def format_report(results: list[HostResult]) -> str:
    lines = [f"{'✓' if r.ok else '✗'} {r.name}\n    {r.detail}" for r in results]
    bad = [r for r in results if not r.ok]
    blocked = [r for r in results if r.ok and r.status in (403, 451)]
    if blocked:
        lines.append("\nHTTP 403/451 у некоторых серверов — возможно, доступ режет провайдер, "
                     "файрвол или прокси (сервер ответил, но не пустил).")
    if bad:
        lines.append("\nХосты со знаком ✗ не отвечают с этого компьютера — это сеть, "
                     "провайдер или VPN, а не ошибка лаунчера.")
    elif not blocked:
        lines.append("\nВсе серверы доступны.")
    return "\n".join(lines)


def summarize(results: list[HostResult]) -> tuple[str, str]:
    """Короткий статус для строки состояния: (текст, уровень)."""
    bad = [r for r in results if not r.ok]
    blocked = [r for r in results if r.ok and r.status in (403, 451)]
    if bad:
        return f"Недоступно серверов: {len(bad)} из {len(results)}", "warn"
    if blocked:
        return f"Диагностика: {len(blocked)} сервер(ов) ответили 403/451 — возможна блокировка", "warn"
    return "Диагностика: все серверы доступны", "ok"
