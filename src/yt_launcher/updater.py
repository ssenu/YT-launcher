"""GitHub Releases 기반 업데이트 확인·다운로드·설치 실행."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from packaging.version import InvalidVersion, Version

from .version import REPO, __version__

API_URL = "https://api.github.com/repos/{repo}/releases/latest"
INSTALLER_RE = re.compile(r"^YT-Launcher-Setup-[\w.\-]+\.exe$")
SUMS_NAME = "SHA256SUMS.txt"
TIMEOUT = 10
CHUNK = 64 * 1024
SILENT_ARGS = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]

Progress = Callable[[int, int], object]


class UpdateError(Exception):
    pass


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    size: int


@dataclass(frozen=True)
class Release:
    tag: str
    version: str
    html_url: str
    installer: Asset | None
    sums: Asset | None


def _request(url: str, accept: str) -> Request:
    return Request(url, headers={"User-Agent": f"YT-Launcher/{__version__}", "Accept": accept})


def parse_release(data: dict) -> Release | None:
    if data.get("draft") or data.get("prerelease"):
        return None
    tag = str(data.get("tag_name") or "")
    if not tag:
        return None
    assets = [
        Asset(str(a["name"]), str(a["browser_download_url"]), int(a.get("size", 0)))
        for a in data.get("assets", [])
    ]
    return Release(
        tag=tag,
        version=tag.lstrip("vV"),
        html_url=str(data.get("html_url") or ""),
        installer=next((a for a in assets if INSTALLER_RE.match(a.name)), None),
        sums=next((a for a in assets if a.name == SUMS_NAME), None),
    )


def is_newer(candidate: str, current: str) -> bool:
    try:
        return Version(candidate.lstrip("vV")) > Version(current.lstrip("vV"))
    except InvalidVersion:
        return False


def fetch_latest(repo: str = REPO, opener=urlopen) -> Release | None:
    """최신 정식 릴리스. 릴리스가 아직 없으면 None, 확인 실패면 UpdateError."""
    request = _request(API_URL.format(repo=repo), "application/vnd.github+json")
    try:
        with opener(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise UpdateError(f"릴리스 정보를 가져오지 못했습니다: {exc}") from exc
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise UpdateError(f"릴리스 정보를 가져오지 못했습니다: {exc}") from exc
    if not isinstance(data, dict):
        return None
    try:
        return parse_release(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise UpdateError(f"릴리스 정보 형식이 올바르지 않습니다: {exc}") from exc


def parse_sums(text: str) -> dict[str, str]:
    """sha256sum 형식("<hash>  <name>" 또는 "<hash> *<name>")을 {이름: 해시}로."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            result[parts[1].lstrip("*").strip()] = parts[0].lower()
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(
    asset: Asset,
    dest: Path,
    progress: Progress | None = None,
    opener=urlopen,
    expected_sha256: str | None = None,
) -> Path:
    """`.part`로 받으며 해시를 계산하고, 성공(해시 일치 포함)한 뒤에만 최종 이름으로 옮긴다."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    digest = hashlib.sha256()
    done = 0
    try:
        try:
            with opener(_request(asset.url, "application/octet-stream"), timeout=TIMEOUT) as response, open(
                partial, "wb"
            ) as out:
                while chunk := response.read(CHUNK):
                    out.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, asset.size)
            if expected_sha256 is not None and digest.hexdigest() != expected_sha256.lower():
                raise UpdateError("설치 파일 해시가 일치하지 않습니다.")
            os.replace(partial, dest)
        except (OSError, http.client.HTTPException) as exc:
            raise UpdateError(f"다운로드 실패: {exc}") from exc
    finally:
        partial.unlink(missing_ok=True)
    return dest


def download_and_verify(
    release: Release, dest_dir: Path, progress: Progress | None = None, opener=urlopen
) -> Path:
    if release.installer is None or release.sums is None:
        raise UpdateError("릴리스에 설치 파일 또는 SHA256SUMS.txt가 없습니다.")
    sums_path = download(release.sums, dest_dir / SUMS_NAME, opener=opener)
    try:
        sums_text = sums_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise UpdateError(f"SHA256SUMS.txt를 읽지 못했습니다: {exc}") from exc
    expected = parse_sums(sums_text).get(release.installer.name)
    if not expected:
        raise UpdateError("SHA256SUMS.txt에 설치 파일 해시가 없습니다.")
    installer_path = dest_dir / release.installer.name
    installer_path.unlink(missing_ok=True)
    return download(release.installer, installer_path, progress, opener, expected_sha256=expected)


def launch_installer(path: Path, popen=subprocess.Popen) -> None:
    """설치 프로그램을 조용한 모드로 분리 실행한다. 호출 후 앱은 곧바로 종료해야 한다."""
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    popen([str(path), *SILENT_ARGS], creationflags=flags, close_fds=True)
