"""크롬으로 유튜브 검색 결과를 연다."""

from __future__ import annotations

import os
import subprocess
import webbrowser
import winreg
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import quote_plus

from . import win32

SEARCH_URL = "https://www.youtube.com/results?search_query="
APP_PATHS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
CHROME_SUBPATH = Path("Google") / "Chrome" / "Application" / "chrome.exe"
ENV_ROOTS = ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")


def build_search_url(query: str) -> str:
    return SEARCH_URL + quote_plus(query.strip())


def registry_chrome_path() -> Path | None:
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, APP_PATHS_KEY) as key:
                value, _ = winreg.QueryValueEx(key, "")
        except OSError:
            continue
        path = Path(str(value).strip().strip('"'))
        if path.is_file():
            return path
    return None


def candidate_paths(env: Mapping[str, str]) -> list[Path]:
    return [Path(env[var]) / CHROME_SUBPATH for var in ENV_ROOTS if env.get(var)]


def find_chrome(
    registry_lookup: Callable[[], Path | None] = registry_chrome_path,
    env: Mapping[str, str] | None = None,
) -> Path | None:
    found = registry_lookup()
    if found:
        return found
    for path in candidate_paths(os.environ if env is None else env):
        if path.is_file():
            return path
    return None


def open_search(
    query: str,
    chrome_path: Path | None,
    *,
    popen: Callable = subprocess.Popen,
    focus: Callable[[], object] = win32.focus_chrome_window,
    browser_open: Callable[[str], object] = webbrowser.open,
    allow_foreground: Callable[[], object] = win32.allow_any_foreground,
) -> bool:
    """검색 결과를 연다. 크롬을 썼으면 True, 기본 브라우저로 폴백했으면 False.

    크롬이 이미 실행 중이면 기존 창에 새 탭으로 열리고, focus()가 그 창을 최대화한다.
    폴링 대기가 있으므로 UI 스레드가 아닌 곳에서 호출한다.
    """
    url = build_search_url(query)
    if chrome_path is None:
        browser_open(url)
        return False
    allow_foreground()
    popen([str(chrome_path), url], close_fds=True)
    focus()
    return True
