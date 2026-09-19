"""
Получение и установка сборки. БЕЗ GitHub API и БЕЗ Releases — просто репозиторий.

Источники (у обоих одинаковый интерфейс):
    latest_version() -> str   версия сборки (для GitHub — хэш последнего коммита)
    fetch(work_dir, cb) -> Path   папка с содержимым сборки

    GithubUpdater — скачивает репозиторий zip-архивом с codeload.github.com;
    LocalUpdater  — берёт файлы из локальной папки test_release/ (тестовый режим).

Что может лежать в репозитории — определяется автоматически (install_pack):
    1. файл *.mrpack в корне;
    2. распакованный .mrpack: modrinth.index.json (+ overrides/);
    3. обычная папка клиента: mods/, config/, ... — копируется в клиент как есть.
       Необязательный pack.json задаёт версии: {"minecraft": "1.21.1", "neoforge": "21.1.77"}.
"""
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests

from app.utils import describe_error, log, sha1_file, sha512_file

GITHUB_WEB = "https://github.com"
GITHUB_CODELOAD = "https://codeload.github.com"

# (время на подключение, время ожидания данных) — чтобы не «висеть» по 20+ секунд
API_TIMEOUT = (5, 15)
DOWNLOAD_TIMEOUT = (10, 60)

ProgressCb = Optional[Callable[[str, int, int, str], None]]


class UpdateError(Exception):
    pass


def network_error(action: str, e: Exception) -> UpdateError:
    """Превращает ошибки requests в понятное сообщение (подробности уходят в лог)."""
    log.warning(f"{action}: {type(e).__name__}: {e}")
    return UpdateError(f"{action}: {describe_error(e)}")


# ============================================================
#                       GitHub (репозиторий)
# ============================================================

def parse_refs(data: bytes) -> dict[str, str]:
    """Разбор ответа git info/refs (pkt-line): {'refs/heads/main': '<sha>', 'HEAD': '<sha>'}."""
    refs: dict[str, str] = {}
    i = 0
    while i + 4 <= len(data):
        n = int(data[i:i + 4], 16)
        if n == 0:                      # flush-пакет
            i += 4
            continue
        line = data[i + 4:i + n]
        i += n
        if line.startswith(b"#"):       # «# service=git-upload-pack»
            continue
        line = line.split(b"\0")[0].strip()   # после \0 идут capabilities
        sha, _, name = line.decode("utf-8", "replace").partition(" ")
        if name:
            refs[name] = sha
    return refs


class GithubUpdater:
    """
    Версия = хэш последнего коммита ветки (берётся обычным git-протоколом с github.com,
    без api.github.com и его лимита в 60 запросов/час). Сборка = zip-архив этого коммита.
    Репозиторий должен быть публичным.
    """

    def __init__(self, repo: str, branch: str = "main"):
        self.repo = repo.strip("/")
        self.branch = (branch or "").strip()
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "MyMinecraftLauncher/1.0"
        self._sha: str | None = None

    def latest_version(self) -> str:
        url = f"{GITHUB_WEB}/{self.repo}.git/info/refs?service=git-upload-pack"
        try:
            r = self.session.get(url, timeout=API_TIMEOUT,
                                 headers={"User-Agent": "git/2.43.0"})
        except requests.exceptions.RequestException as e:
            raise network_error("Проверка обновлений", e) from e
        if r.status_code in (401, 404):   # для несуществующих/приватных репозиториев GitHub отвечает 401
            raise UpdateError(f"Репозиторий {self.repo} не найден или приватный. "
                              f"Проверьте GITHUB_REPO в app/config.py.")
        if r.status_code >= 400:
            raise UpdateError(f"GitHub: HTTP {r.status_code}")

        refs = parse_refs(r.content)
        name = f"refs/heads/{self.branch}" if self.branch else "HEAD"
        sha = refs.get(name)
        if not sha:
            raise UpdateError(f"Ветка '{self.branch}' не найдена в {self.repo}.")
        self._sha = sha
        return sha

    def fetch(self, work_dir: Path, progress_cb: Optional[Callable[[int, int], None]] = None) -> Path:
        """Скачивает архив репозитория и распаковывает. Возвращает папку с содержимым."""
        sha = self._sha or self.latest_version()
        work_dir.mkdir(parents=True, exist_ok=True)
        zip_path = work_dir / "repo.zip"
        extract_dir = work_dir / "repo"

        url = f"{GITHUB_CODELOAD}/{self.repo}/zip/{sha}"
        try:
            with self.session.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as r:
                if r.status_code >= 400:
                    raise UpdateError(f"Не удалось скачать репозиторий: HTTP {r.status_code}")
                total = int(r.headers.get("Content-Length", 0))  # у codeload обычно 0 (неизвестно)
                done = 0
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        if progress_cb:
                            progress_cb(done, total)
        except requests.exceptions.RequestException as e:
            raise network_error("Скачивание репозитория", e) from e

        shutil.rmtree(extract_dir, ignore_errors=True)
        try:
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(extract_dir)
        except zipfile.BadZipFile as e:
            raise UpdateError("Скачанный архив повреждён — повторите обновление.") from e
        finally:
            zip_path.unlink(missing_ok=True)
        return _single_root(extract_dir)


def _single_root(d: Path) -> Path:
    """В архиве GitHub всё лежит в одной папке «repo-<sha>/» — заходим в неё."""
    entries = list(d.iterdir())
    return entries[0] if len(entries) == 1 and entries[0].is_dir() else d


# ============================================================
#                  Локальный источник (тест)
# ============================================================

class LocalUpdater:
    """
    Тестовый режим: содержимое «репозитория» лежит в папке test_release/.
    Формат тот же, что и в GitHub-репозитории (см. начало файла).
    Версия: version.txt -> имя .mrpack -> отпечаток по времени изменения файлов
    (поменяли файл в папке — лаунчер снова предложит обновление).
    """

    def __init__(self, release_dir: Path):
        self.dir = release_dir

    def latest_version(self) -> str:
        if not self.dir.is_dir() or not any(self.dir.iterdir()):
            raise UpdateError(f"Папка {self.dir} пуста или не существует. Положите туда сборку "
                              f"(.mrpack или файлы клиента).")
        vfile = self.dir / "version.txt"
        if vfile.exists():
            return vfile.read_text(encoding="utf-8").strip()
        mrpacks = sorted(self.dir.glob("*.mrpack"))
        if mrpacks:
            return mrpacks[0].stem
        newest = max(p.stat().st_mtime for p in self.dir.rglob("*") if p.is_file())
        return f"local-{int(newest)}"

    def fetch(self, work_dir: Path, progress_cb=None) -> Path:
        return self.dir  # копировать не нужно — ставим прямо из папки


# ============================================================
#                        Установка сборки
# ============================================================

def install_pack(root: Path, target_dir: Path, progress_cb: ProgressCb = None) -> dict:
    """
    Ставит сборку из папки root в target_dir. Формат определяется сам:
    *.mrpack -> распакованный mrpack -> обычная папка клиента.
    Возвращает info: {minecraft?, neoforge?, failed, ...}.
    """
    mrpacks = sorted(root.glob("*.mrpack"))
    if mrpacks:
        log.info(f"Формат сборки: .mrpack ({mrpacks[0].name})")
        return install_mrpack(mrpacks[0], target_dir, progress_cb)

    if (root / "modrinth.index.json").exists():
        log.info("Формат сборки: распакованный mrpack")
        with tempfile.TemporaryDirectory() as tmp:
            archive = shutil.make_archive(str(Path(tmp) / "pack"), "zip", root)
            return install_mrpack(Path(archive), target_dir, progress_cb)

    log.info("Формат сборки: папка клиента")
    return install_plain(root, target_dir, progress_cb)


# --- обычная папка клиента ---------------------------------------------------

_SKIP_TOP_DIRS = {".git", ".github"}
_SKIP_TOP_FILES = {".gitignore", ".gitattributes", ".gitmodules", "pack.json", "version.txt"}
_SKIP_TOP_PREFIXES = ("readme", "license", "licence", "changelog")


def _pack_files(root: Path) -> list[Path]:
    """Файлы сборки (относительные пути) без служебных файлов репозитория."""
    files = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        top = rel.parts[0]
        if top in _SKIP_TOP_DIRS:
            continue
        if len(rel.parts) == 1 and (top in _SKIP_TOP_FILES
                                    or top.lower().startswith(_SKIP_TOP_PREFIXES)):
            continue
        files.append(rel)
    return files


def _read_pack_json(root: Path) -> dict:
    f = root / "pack.json"
    if not f.exists():
        return {}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        raise UpdateError(f"pack.json повреждён: {e}") from e
    return {k: data[k] for k in ("minecraft", "neoforge") if isinstance(data.get(k), str)}


def install_plain(root: Path, target_dir: Path, progress_cb: ProgressCb = None) -> dict:
    target_dir.mkdir(parents=True, exist_ok=True)
    files = _pack_files(root)
    total = len(files)
    if not total:
        raise UpdateError("В репозитории нет файлов сборки.")

    copied = skipped = 0
    for idx, rel in enumerate(files, start=1):
        src, dst = root / rel, target_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.stat().st_size == src.stat().st_size \
                and sha1_file(dst) == sha1_file(src):
            skipped += 1
            stage = "skip"
        else:
            shutil.copyfile(src, dst)
            copied += 1
            stage = "copy"
        if progress_cb:
            progress_cb(stage, idx, total, rel.as_posix())

    removed = _sync_mods(root, target_dir)
    log.info(f"Папка клиента: скопировано {copied}, без изменений {skipped}, "
             f"удалено старых модов {removed}")
    info = {"failed": 0, "copied": copied, "skipped": skipped, "removed": removed}
    info.update(_read_pack_json(root))
    return info


def _sync_mods(root: Path, target_dir: Path) -> int:
    """Удаляет из клиентского mods/ .jar, которых больше нет в репозитории
    (иначе старая и новая версии мода лежат вместе, и игра падает)."""
    src, dst = root / "mods", target_dir / "mods"
    if not src.is_dir() or not dst.is_dir():
        return 0
    keep = {p.name for p in src.iterdir() if p.is_file()}
    removed = 0
    for p in dst.iterdir():
        if p.is_file() and p.suffix.lower() == ".jar" and p.name not in keep:
            p.unlink()
            removed += 1
    return removed


# --- .mrpack -----------------------------------------------------------------

def _download_plain(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)


def read_mrpack_index(mrpack_path: Path) -> dict:
    with zipfile.ZipFile(mrpack_path, "r") as z:
        if "modrinth.index.json" not in z.namelist():
            raise UpdateError("Это не .mrpack (нет modrinth.index.json).")
        with z.open("modrinth.index.json") as f:
            return json.loads(f.read().decode("utf-8"))


def install_mrpack(mrpack_path: Path, target_dir: Path,
                   progress_cb: ProgressCb = None) -> dict:
    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded = skipped = failed = 0

    with zipfile.ZipFile(mrpack_path, "r") as z:
        with z.open("modrinth.index.json") as f:
            index = json.loads(f.read().decode("utf-8"))

        deps = index.get("dependencies", {})
        info = {
            "minecraft": deps.get("minecraft", ""),
            "neoforge": deps.get("neoforge", "") or deps.get("forge", ""),
            "version": index.get("versionId", "0.0.0"),
        }

        # overrides
        for member in z.namelist():
            if member.startswith("overrides/") and not member.endswith("/"):
                rel = member[len("overrides/"):]
                dst = target_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as src, open(dst, "wb") as out:
                    shutil.copyfileobj(src, out)

        # files
        files = index.get("files", [])
        total = len(files)
        log.info(f"mrpack: файлов к проверке {total}")

        for idx, entry in enumerate(files, start=1):
            rel = entry["path"]
            dst = target_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)

            if entry.get("env", {}).get("client") == "unsupported":
                continue

            hashes = entry.get("hashes", {})
            want_sha1 = (hashes.get("sha1") or "").lower()
            want_sha512 = (hashes.get("sha512") or "").lower()

            if dst.exists():
                try:
                    if want_sha1 and sha1_file(dst) == want_sha1:
                        skipped += 1
                        if progress_cb:
                            progress_cb("skip", idx, total, rel)
                        continue
                    if want_sha512 and sha512_file(dst) == want_sha512:
                        skipped += 1
                        if progress_cb:
                            progress_cb("skip", idx, total, rel)
                        continue
                except Exception:
                    pass

            urls = entry.get("downloads", [])
            if not urls:
                continue

            if progress_cb:
                progress_cb("download", idx, total, rel)

            last_err = None
            for url in urls:
                try:
                    _download_plain(url, dst)
                    break
                except Exception as e:
                    last_err = e
                    log.warning(f"Ошибка {url}: {e}")
            else:
                failed += 1
                log.error(f"Не удалось скачать {rel}: {last_err}")
                continue

            if want_sha1 and sha1_file(dst) != want_sha1:
                dst.unlink(missing_ok=True)
                failed += 1
                continue

            downloaded += 1

    log.info(f"mrpack: скачано {downloaded}, пропущено {skipped}, ошибок {failed}")
    info.update(downloaded=downloaded, skipped=skipped, failed=failed)
    return info
