"""
Установка и запуск Minecraft + NeoForge.
Использует minecraft-launcher-lib 8.x.
"""
import hashlib
import shutil
import subprocess
import sys
import time
import uuid as uuidlib
from pathlib import Path

import minecraft_launcher_lib
from minecraft_launcher_lib.types import CallbackDict

from app.config import LOGS_DIR
from app.utils import describe_error, log


class MinecraftError(Exception):
    pass


# ---------- Java ----------

def find_java(custom_path: str = "") -> str:
    """Ищет Java. custom_path — из настроек, если указан."""
    if custom_path:
        p = Path(custom_path)
        if p.is_file():
            return str(p)
        if p.is_dir():
            for j in p.rglob("java.exe"):
                return str(j)

    java = shutil.which("java") or shutil.which("java.exe")
    if java:
        return java

    candidates = [
        r"C:\Program Files\Java",
        r"C:\Program Files\Eclipse Adoptium",
        r"C:\Program Files\Microsoft",
        r"E:\UTILS\JAVA",
    ]
    for base in candidates:
        p = Path(base)
        if p.exists():
            for java_exe in p.rglob("java.exe"):
                return str(java_exe)

    raise MinecraftError("Java 21 не найдена. Установите JDK 21 или укажите путь в настройках.")


# ---------- Подготовка ----------

def ensure_dirs(game_dir: Path) -> None:
    for sub in ["client", "minecraft"]:
        (game_dir / sub).mkdir(parents=True, exist_ok=True)


# ---------- Callback ----------

def _make_callback(progress_cb) -> CallbackDict:
    if progress_cb is None:
        return CallbackDict({})
    state = {"total": 0, "current": 0, "status": ""}

    def set_status(text):
        state["status"] = text or ""
        progress_cb(state["status"], state["current"], state["total"])

    def set_progress(v):
        state["current"] = int(v or 0)
        progress_cb(state["status"], state["current"], state["total"])

    def set_max(v):
        state["total"] = int(v or 0)
        progress_cb(state["status"], state["current"], state["total"])

    return CallbackDict({
        "setStatus": set_status,
        "setProgress": set_progress,
        "setMax": set_max,
    })


# ---------- Установка ----------

def install_minecraft(mc_dir: Path, mc_version: str,
                      java_path: str = "", progress_cb=None) -> None:
    find_java(java_path)
    log.info(f"Установка Minecraft {mc_version} в {mc_dir}")
    try:
        minecraft_launcher_lib.install.install_minecraft_version(
            mc_version, str(mc_dir), callback=_make_callback(progress_cb)
        )
    except Exception as e:
        log.exception("install_minecraft failed")
        raise MinecraftError(f"Не удалось установить Minecraft: {describe_error(e)}")
    log.info(f"Minecraft {mc_version} установлен")


def install_neoforge(mc_dir: Path, mc_version: str, nf_version: str,
                     java_path: str = "", progress_cb=None) -> None:
    java = find_java(java_path)
    log.info(f"Установка NeoForge {nf_version} для MC {mc_version}")
    try:
        loader = minecraft_launcher_lib.mod_loader.get_mod_loader("neoforge")
        loader.install(
            minecraft_version=mc_version,
            minecraft_directory=str(mc_dir),
            callback=_make_callback(progress_cb),
            java=java,
            loader_version=nf_version,
        )
    except Exception as e:
        log.exception("install_neoforge failed")
        raise MinecraftError(f"Не удалось установить NeoForge: {describe_error(e)}")
    log.info(f"NeoForge {nf_version} установлен")


# ---------- Версии ----------

def installed_version_ids(mc_dir: Path) -> list[str]:
    try:
        return [v["id"] for v in minecraft_launcher_lib.utils.get_installed_versions(str(mc_dir))]
    except Exception:
        return []


def _neoforge_version_id(mc_dir: Path, nf_version: str) -> str | None:
    ids = installed_version_ids(mc_dir)
    wanted = f"neoforge-{nf_version}"
    if wanted in ids:
        return wanted
    for vid in ids:
        if "neoforge" in vid.lower() and nf_version in vid:
            return vid
    return None


# ---------- Offline UUID ----------

def offline_uuid(username: str) -> str:
    return str(uuidlib.UUID(bytes=hashlib.md5(f"OfflinePlayer:{username}".encode()).digest()))


# ---------- Команда запуска ----------

def build_launch_command(
    mc_dir: Path,
    client_dir: Path,
    username: str,
    token: str,
    mc_version: str,
    nf_version: str,
    ram_mb: int,
    java_path: str = "",
) -> list[str]:
    if nf_version:
        version_id = _neoforge_version_id(mc_dir, nf_version)
        if not version_id:
            raise MinecraftError(f"NeoForge {nf_version} не найден в {mc_dir / 'versions'}")
    else:
        version_id = mc_version

    options = {
        "username": username,
        "uuid": offline_uuid(username),
        "token": token or "0",
        "executablePath": find_java(java_path),
        "jvmArguments": [
            f"-Xmx{ram_mb}M",
            f"-Xms{min(ram_mb, 1024)}M",
        ],
        "gameDirectory": str(client_dir),
        "launcherName": "MyLauncher",
        "launcherVersion": "1.0.0",
        "userType": "legacy",
    }

    try:
        return minecraft_launcher_lib.command.get_minecraft_command(
            version_id, str(mc_dir), options
        )
    except Exception as e:
        log.exception("build command failed")
        raise MinecraftError(f"Не удалось собрать команду запуска: {e}")


# ---------- Запуск ----------

GAME_LOG = LOGS_DIR / "minecraft.log"   # вывод игры (только последний запуск)
STARTUP_CHECK_SEC = 3.0                 # столько ждём: не упала ли игра сразу

_IS_WINDOWS = sys.platform == "win32"
# Флаги создания процесса Windows (литералами, чтобы модуль импортировался на любой ОС)
_DETACHED_PROCESS = 0x00000008          # без консоли, не привязан к консоли лаунчера
_CREATE_NEW_PROCESS_GROUP = 0x00000200  # своя группа: Ctrl+C/закрытие консоли лаунчера не достанут
_CREATE_BREAKAWAY_FROM_JOB = 0x01000000 # вне Job-объекта: закрытие лаунчера не убьёт игру


def _spawn_detached(cmd: list[str], cwd: Path, out) -> subprocess.Popen:
    """Запускает процесс полностью независимо от лаунчера."""
    kwargs = dict(cwd=str(cwd), stdin=subprocess.DEVNULL, stdout=out,
                  stderr=subprocess.STDOUT, close_fds=True)
    if _IS_WINDOWS:
        flags = _DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP
        try:
            return subprocess.Popen(cmd, creationflags=flags | _CREATE_BREAKAWAY_FROM_JOB, **kwargs)
        except PermissionError:
            # Job-объект запрещает выход из него — запускаем без этого флага
            return subprocess.Popen(cmd, creationflags=flags, **kwargs)
    return subprocess.Popen(cmd, start_new_session=True, **kwargs)


def _log_tail(lines: int = 3) -> str:
    try:
        text = GAME_LOG.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    tail = [l.strip() for l in text.splitlines() if l.strip()][-lines:]
    return (": " + " | ".join(tail))[:220] if tail else ""


def launch_minecraft(cmd: list[str], cwd: Path) -> int:
    """
    Запускает игру ОТДЕЛЬНЫМ процессом: она живёт сама по себе, даже если закрыть лаунчер.
    Вывод пишется в logs/minecraft.log. Возвращает PID.
    Если игра упала в первые секунды (например, не та версия Java) — MinecraftError с причиной.
    """
    log.info("Запуск Minecraft (отдельным процессом)")
    try:
        GAME_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(GAME_LOG, "wb") as out:   # процесс получает свою копию дескриптора
            proc = _spawn_detached(cmd, cwd, out)
    except Exception as e:
        log.exception("launch failed")
        raise MinecraftError(f"Ошибка запуска Minecraft: {e}")

    deadline = time.monotonic() + STARTUP_CHECK_SEC
    while time.monotonic() < deadline:
        code = proc.poll()
        if code is not None:
            log.error(f"Minecraft завершился сразу, код {code}")
            raise MinecraftError(f"Игра сразу закрылась (код {code}){_log_tail()}. "
                                 f"Полный лог: {GAME_LOG}")
        time.sleep(0.1)

    log.info(f"Minecraft запущен, PID {proc.pid}")
    return proc.pid