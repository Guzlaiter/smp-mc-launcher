import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

CONFIG_PATH = DATA_DIR / "config.json"

# ============================================================
#   ЗАШИТЫЙ РЕПОЗИТОРИЙ — правится только здесь
# ============================================================
GITHUB_REPO = "owner/repo"          # ← вписать свой owner/repo

# Если эта папка существует и содержит .mrpack — берём релиз из неё,
# GitHub не дёргается. Для отладки.
TEST_RELEASE_DIR = ROOT / "test_release"


DEFAULT_CONFIG = {
    "game_directory": str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MyMinecraft"),
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
    """True, если в test_release/ есть .mrpack."""
    if not TEST_RELEASE_DIR.exists():
        return False
    return any(TEST_RELEASE_DIR.glob("*.mrpack"))