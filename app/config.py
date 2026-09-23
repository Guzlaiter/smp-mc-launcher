import json
import os
import sys
import tempfile
from pathlib import Path


def _app_root() -> Path:
    """
    Папка, рядом с которой лежат data/ и logs/.

    Обычный запуск (python main.py): __file__ указывает на файл на диске —
    ROOT = папка проекта, как и раньше.

    .exe из PyInstaller: __file__ указывает во временную папку распаковки
    (sys._MEIPASS), которая создаётся заново при каждом запуске и удаляется
    при закрытии — папки data/logs исчезали бы вместе с ней. Поэтому в этом
    случае берём папку, где лежит сам .exe (sys.executable), а не __file__.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _writable_dir(preferred: Path, name: str) -> Path:
    """
    Создаёт preferred/name; если нет прав на запись (например, .exe лежит
    в Program Files) — использует %LOCALAPPDATA%/MyMinecraftLauncher/name,
    а не падает молча ещё до открытия окна лаунчера.
    """
    try:
        d = preferred / name
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return d
    except OSError:
        fallback = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
        d = fallback / "MyMinecraftLauncher" / name
        d.mkdir(parents=True, exist_ok=True)
        return d


ROOT = _app_root()
DATA_DIR = _writable_dir(ROOT, "data")
LOGS_DIR = _writable_dir(ROOT, "logs")
GAME_DIR = _writable_dir(ROOT, "game")

CONFIG_PATH = DATA_DIR / "config.json"

# ============================================================
#   ЗАШИТЫЙ РЕПОЗИТОРИЙ — правится только здесь
# ============================================================
GITHUB_REPO = "adsltwitchgaming-collab/SMPCreateUpdate"          # ← вписать свой owner/repo
GITHUB_BRANCH = "main"              # ветка, из которой берётся сборка
IP_SERVER = "createlandsmp.play.ski:25565"

# ============================================================
#   ИСТОЧНИК СБОРКИ
# ============================================================
# True  — тестовый режим: сборка берётся из локальной папки TEST_RELEASE_DIR
#         (сборка в том же формате, что и в репозитории), GitHub вообще не дёргается.
# False — боевой режим: сборка берётся из репозитория GITHUB_REPO (zip-архив ветки GITHUB_BRANCH).
#         Релизы и GitHub API не используются.
#
# Что лежит в репозитории (и в test_release/) — определяется автоматически:
#   1. файл *.mrpack                              — ставится как модпак Modrinth;
#   2. modrinth.index.json + overrides/           — то же, но распакованное;
#   3. обычная папка клиента (mods/, config/, ...) — копируется как есть;
#      необязательный pack.json задаёт версии: {"minecraft": "1.21.1", "neoforge": "21.1.77"}
TEST_LOCAL_MODPACK = False
TEST_RELEASE_DIR = ROOT / "test_release"


DEFAULT_CONFIG = {
    "game_directory": str(Path(GAME_DIR).resolve()),
    "minecraft_version": "1.21.1",
    "neoforge_version": "",
    "ram_mb": 4096,
    "close_after_launch": False,
    "username": "Player",
    "server_name": "MY SERVER",
    "auto_check_updates": True,
    "java_path": "",
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # убираем возможные остатки старых ключей
            for old in ("github_repo", "github_token"):
                data.pop(old, None)
            for k, v in DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")


def is_test_mode() -> bool:
    """Тестовый режим включается только флагом TEST_LOCAL_MODPACK выше."""
    return bool(TEST_LOCAL_MODPACK)