"""
Установка и запуск Minecraft + NeoForge.
Использует minecraft-launcher-lib 8.x.
"""
import hashlib
import shutil
import subprocess
import uuid as uuidlib
from pathlib import Path

import minecraft_launcher_lib
from minecraft_launcher_lib.types import CallbackDict

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
            raise MinecraftError(
                f"NeoForge {nf_version} не найден в {mc_dir / 'versions'}"
            )
    else:
        version_id = mc_version

    jvm_args = [
        # G1GC
        "-XX:+UseG1GC",
        "-XX:+ParallelRefProcEnabled",
        "-XX:MaxGCPauseMillis=200",
        "-XX:+UnlockExperimentalVMOptions",
        "-XX:+DisableExplicitGC",

        # G1 настройки
        "-XX:G1NewSizePercent=30",
        "-XX:G1MaxNewSizePercent=40",
        "-XX:G1HeapRegionSize=8M",
        "-XX:G1ReservePercent=20",
        "-XX:G1HeapWastePercent=5",
        "-XX:G1MixedGCCountTarget=4",
        "-XX:InitiatingHeapOccupancyPercent=15",
        "-XX:G1MixedGCLiveThresholdPercent=90",
        "-XX:G1RSetUpdatingPauseTimePercent=5",
        "-XX:SurvivorRatio=32",
        "-XX:+PerfDisableSharedMem",
        "-XX:MaxTenuringThreshold=1",

        # RAM
        f"-Xmx{ram_mb}M",
        f"-Xms{min(ram_mb, 1024)}M",
    ]

    options = {
        "username": username,
        "uuid": offline_uuid(username),
        "token": token or "0",
        "executablePath": find_java(java_path),
        "jvmArguments": jvm_args,
        "gameDirectory": str(client_dir),
        "launcherName": "MyLauncher",
        "launcherVersion": "1.0.0",
        "userType": "legacy",
    }

    try:
        return minecraft_launcher_lib.command.get_minecraft_command(
            version_id,
            str(mc_dir),
            options,
        )

    except Exception as e:
        log.exception("build command failed")
        raise MinecraftError(
            f"Не удалось собрать команду запуска: {e}"
        )


# ---------- Запуск ----------

def launch_minecraft(cmd: list[str], client_dir: Path) -> subprocess.Popen:
    log.info("Запуск Minecraft")

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(client_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

        log.info(f"Minecraft запущен, PID={process.pid}")
        return process

    except Exception as e:
        log.exception("launch failed")
        raise MinecraftError(
            f"Ошибка запуска Minecraft: {describe_error(e)}"
        )