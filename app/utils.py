import hashlib
import logging
import re
from pathlib import Path
from mcstatus import JavaServer

from app.config import LOGS_DIR, IP_SERVER
import requests

from app.config import LOGS_DIR

LOG_PATH = LOGS_DIR / "launcher.log"

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
log = logging.getLogger("launcher")


def sha1_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sha512_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def human_size(num: int) -> str:
    num = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def safe_join(base: Path, rel: str) -> Path:
    """Защита от path traversal."""
    target = (base / rel).resolve()
    base_r = base.resolve()
    if base_r not in target.parents and target != base_r:
        raise ValueError(f"Недопустимый путь: {rel}")
    return target


_HOST_RE = re.compile(r"host='([^']+)'")


def describe_error(e: BaseException) -> str:
    """
    Короткое человеческое описание ошибки. Для сетевых — с ХОСТОМ, который не отвечает
    (например «таймаут сети [maven.neoforged.net]»). Полный текст остаётся в logs/.
    """
    text = str(e)
    m = _HOST_RE.search(text)
    host = f" [{m.group(1)}]" if m else ""
    if isinstance(e, (requests.exceptions.Timeout, TimeoutError)) or "timed out" in text.lower():
        return f"таймаут сети{host}"
    if isinstance(e, requests.exceptions.ConnectionError):
        return f"нет соединения{host}"
    return text

def get_stat():
    server = JavaServer.lookup(IP_SERVER)

    status = server.status()

    SERVER_STATS = [
        ("Игроки:", f"{status.players.online:,} / {status.players.max:,}"),
        ("Пинг:",   f"{round(status.latency)}мс"),
        ("Статус:", f"{ 'Онлайн' if status.latency > 0 else 'Недоступен' }"),
    ]
    return SERVER_STATS