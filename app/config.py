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
    """Тестовый режим включается только флагом TEST_LOCAL_MODPACK выше."""
    return bool(TEST_LOCAL_MODPACK)