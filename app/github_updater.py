"""
Загрузка и обновление сборки:
- из GitHub Releases (основной режим);
- из локальной папки test_release/ (тестовый режим).
"""
import json
import shutil
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests

from app.utils import log, sha1_file, sha512_file


GITHUB_API = "https://api.github.com"


class UpdateError(Exception):
    pass


class GithubUpdater:
    def __init__(self, repo: str):
        self.repo = repo.strip("/")
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["User-Agent"] = "MyMinecraftLauncher/1.0"

    # ---------------- GitHub API ----------------

    def get_latest_release(self) -> dict:
        url = f"{GITHUB_API}/repos/{self.repo}/releases/latest"
        r = self.session.get(url, timeout=20)
        if r.status_code == 404:
            raise UpdateError("Релиз не найден.")
        if r.status_code >= 400:
            raise UpdateError(f"GitHub API: {r.status_code} {r.text[:200]}")
        return r.json()

    def find_mrpack_asset(self, release: dict) -> dict:
        for asset in release.get("assets", []):
            if asset["name"].lower().endswith(".mrpack"):
                return asset
        raise UpdateError("В релизе нет .mrpack файла.")

    def download_asset(self, asset: dict, dest: Path,
                       progress_cb: Optional[Callable[[int, int], None]] = None) -> None:
        url = asset.get("browser_download_url") or asset.get("url")
        headers = {"Accept": "application/octet-stream"}
        with self.session.get(url, headers=headers, stream=True, timeout=300) as r:
            if r.status_code >= 400:
                raise UpdateError(f"Не удалось скачать {asset['name']}: {r.status_code}")
            total = int(r.headers.get("Content-Length", 0)) or asset.get("size", 0)
            done = 0
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    if progress_cb:
                        progress_cb(done, total)

    # ---------------- mrpack ----------------

    @staticmethod
    def read_mrpack_index(mrpack_path: Path) -> dict:
        with zipfile.ZipFile(mrpack_path, "r") as z:
            if "modrinth.index.json" not in z.namelist():
                raise UpdateError("Это не .mrpack (нет modrinth.index.json).")
            with z.open("modrinth.index.json") as f:
                return json.loads(f.read().decode("utf-8"))

    def install_mrpack(self, mrpack_path: Path, target_dir: Path,
                       progress_cb: Optional[Callable[[str, int, int, str], None]] = None) -> dict:
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
                        self._download_plain(url, dst)
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

    @staticmethod
    def _download_plain(url: str, dest: Path) -> None:
        with requests.get(url, stream=True, timeout=180) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)


# ============================================================
#                    ЛОКАЛЬНЫЙ ИСТОЧНИК
# ============================================================

class LocalUpdater:
    """
    Берёт сборку из локальной папки test_release/.
    Ожидает:
      - один .mrpack файл;
      - опционально version.txt с версией (если нет — берём из имени файла).
    """

    def __init__(self, release_dir: Path):
        self.dir = release_dir

    def _find_mrpack(self) -> Path:
        files = sorted(self.dir.glob("*.mrpack"))
        if not files:
            raise UpdateError(f"В {self.dir} нет .mrpack файла.")
        return files[0]

    def get_local_version(self) -> str:
        vfile = self.dir / "version.txt"
        if vfile.exists():
            return vfile.read_text(encoding="utf-8").strip()
        # fallback — имя файла без расширения
        return self._find_mrpack().stem

    def copy_asset(self, dest: Path,
                   progress_cb: Optional[Callable[[int, int], None]] = None) -> None:
        src = self._find_mrpack()
        dest.parent.mkdir(parents=True, exist_ok=True)
        total = src.stat().st_size
        done = 0
        chunk = 1024 * 1024
        with open(src, "rb") as fi, open(dest, "wb") as fo:
            while True:
                buf = fi.read(chunk)
                if not buf:
                    break
                fo.write(buf)
                done += len(buf)
                if progress_cb:
                    progress_cb(done, total)

    # install_mrpack — тот же самый, переиспользуем
    install_mrpack = GithubUpdater.install_mrpack
    _download_plain = staticmethod(GithubUpdater._download_plain)