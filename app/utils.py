import hashlib
import logging
from pathlib import Path

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