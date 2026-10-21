# YT Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 바탕화면 우상단에 뜨는 타일형 위젯에서 타일을 누르면 크롬이 최대화 창으로 유튜브 검색 결과를 여는 윈도우 앱을, GitHub Releases 설치 프로그램과 원클릭 자동 업데이트까지 포함해 만든다.

**Architecture:** Qt에 의존하지 않는 로직 모듈(`models`, `geometry`, `storage`, `win32`, `chrome`, `autostart`, `updater`)을 먼저 TDD로 만들고, 그 위에 PySide6 UI(`ui/`)와 이들을 연결하는 컨트롤러(`app.py`)를 얹는다. PyInstaller(onedir)로 묶고 Inno Setup으로 사용자 단위 설치 프로그램을 만들며, 태그 push 시 GitHub Actions가 빌드·릴리스한다.

**Tech Stack:** Python 3.14, PySide6-Essentials 6.10+, packaging, pytest, PyInstaller 6.16+, Inno Setup 6, GitHub Actions (windows-latest)

**Spec:** `docs/superpowers/specs/2026-10-21-yt-launcher-design.md`

## Global Constraints

- 저장소: `ssenu/YT-launcher` (`version.REPO`). 업데이트 API: `https://api.github.com/repos/ssenu/YT-launcher/releases/latest`
- 플랫폼: Windows 10/11 x64 전용. `winreg`, `ctypes.WinDLL` 사용 가능.
- Python `>=3.12` (개발·CI는 3.14). 런타임 의존성은 `PySide6-Essentials`, `packaging`만.
- 검색 URL: `https://www.youtube.com/results?search_query=` + `urllib.parse.quote_plus(query.strip())`
- 크롬 창은 `SW_MAXIMIZE`(최대화). F11 전체화면 금지.
- 런처 창: `FramelessWindowHint | Tool | WindowStaysOnBottomHint`, 작업표시줄 미표시, 트레이 아이콘만.
- 기본 위치/크기: 주 모니터 작업 영역 우상단, 여백 16px, 360×480. 최소 240×200. 위치 저장 디바운스 500ms.
- 설정 파일: `%APPDATA%\YT-Launcher\config.json` (원자적 저장), 손상 시 `config.json.bak`. 로그: `%APPDATA%\YT-Launcher\logs\launcher.log` (1MB × 3).
- 타일 팔레트 8색: `#E53935 #D81B60 #8E24AA #3949AB #1E88E5 #00897B #43A047 #F4511E`
- 업데이트 확인: 시작 30초 후 1회, 이후 24시간마다, 수동 메뉴. 설치 파일 이름 `YT-Launcher-Setup-<버전>.exe`, 해시 파일 `SHA256SUMS.txt`.
- 조용한 설치 인자: `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
- 단일 인스턴스: QLocalServer 이름 `YTLauncher-<사용자명>`, Win32 mutex `YTLauncherMutex`.
- 자동 실행 Run 키: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, 값 이름 `YTLauncher`.
- 설치 경로: `{localappdata}\Programs\YT-Launcher`, 관리자 권한 불필요(`PrivilegesRequired=lowest`), exe 이름 `YTLauncher.exe`.
- UI 문구는 한국어.
- 모든 명령은 저장소 루트(`C:\MyCode\YT-Launcher`)에서 PowerShell로 실행. 파이썬은 `.venv\Scripts\python`.

## File Structure

```
pyproject.toml                       # 패키지·의존성·pytest 설정
launcher.py                          # PyInstaller 진입 스크립트
src/yt_launcher/
  __init__.py
  __main__.py                        # python -m yt_launcher
  version.py                         # __version__, APP_NAME, REPO, MUTEX_NAME
  models.py                          # Tile, PALETTE, auto_color
  geometry.py                        # Rect, default_rect, is_visible_on_any
  storage.py                         # Config, Storage, default_dir
  win32.py                           # ctypes 래퍼 (창 찾기/최대화/최하단/소유자/mutex)
  chrome.py                          # build_search_url, find_chrome, open_search
  autostart.py                       # AutoStart, RunKeyBackend, launch_command
  updater.py                         # Release/Asset, fetch_latest, download_and_verify, launch_installer
  resources.py                       # asset_path, app_icon
  assets/icon.png, assets/icon.ico   # tools/make_icon.py로 생성
  single_instance.py                 # SingleInstance (QLocalServer)
  app.py                             # LauncherApp 컨트롤러
  main.py                            # main(), setup_logging()
  ui/__init__.py
  ui/tile_grid.py                    # TileGrid, TileDelegate
  ui/tile_dialog.py                  # TileDialog
  ui/launcher_window.py              # LauncherWindow, Header
  ui/tray.py                         # Tray
tools/make_icon.py                   # 아이콘 생성 스크립트
scripts/build.ps1                    # PyInstaller + Inno Setup + SHA256SUMS
installer/setup.iss                  # Inno Setup 스크립트
.github/workflows/ci.yml             # push 시 테스트
.github/workflows/release.yml        # v* 태그 시 빌드·릴리스
docs/manual-test-checklist.md        # 릴리스 전 수동 점검표
README.md
tests/conftest.py, tests/test_*.py
```

---

### Task 1: 프로젝트 기반

**Files:**
- Create: `pyproject.toml`, `src/yt_launcher/__init__.py`, `src/yt_launcher/version.py`, `tests/conftest.py`
- Test: `tests/test_version.py`

**Interfaces:**
- Consumes: 없음
- Produces: `yt_launcher.version.__version__: str`, `APP_NAME = "YT Launcher"`, `REPO = "ssenu/YT-launcher"`, `MUTEX_NAME = "YTLauncherMutex"`. pytest fixture `qapp` (세션 범위 `QApplication`, offscreen).

- [ ] **Step 1: 가상환경 생성**

Run:
```powershell
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
```
Expected: `.venv\Scripts\python.exe` 생성.

- [ ] **Step 2: `pyproject.toml` 작성**

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "yt-launcher"
dynamic = ["version"]
description = "바탕화면 타일에서 유튜브 검색을 여는 런처"
requires-python = ">=3.12"
dependencies = [
    "PySide6-Essentials>=6.10",
    "packaging>=24",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pyinstaller>=6.16",
]

[tool.setuptools.dynamic]
version = { attr = "yt_launcher.version.__version__" }

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
yt_launcher = ["assets/*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: 실패하는 테스트 작성** — `tests/test_version.py`

```python
from packaging.version import Version

from yt_launcher import version


def test_version_is_valid_pep440():
    Version(version.__version__)


def test_release_constants():
    assert version.REPO == "ssenu/YT-launcher"
    assert version.APP_NAME == "YT Launcher"
    assert version.MUTEX_NAME == "YTLauncherMutex"
```

`tests/conftest.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pip install pytest packaging; .venv\Scripts\python -m pytest tests/test_version.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher'`

- [ ] **Step 5: 패키지 작성**

`src/yt_launcher/__init__.py`:

```python
"""YT Launcher: 바탕화면 타일에서 유튜브 검색을 연다."""
```

`src/yt_launcher/version.py`:

```python
"""앱 버전과 배포 정보. 릴리스 CI가 __version__ 줄을 태그 값으로 덮어쓴다."""

__version__ = "0.1.0"
APP_NAME = "YT Launcher"
REPO = "ssenu/YT-launcher"
MUTEX_NAME = "YTLauncherMutex"
```

- [ ] **Step 6: 개발 의존성 설치 후 테스트 통과 확인**

Run: `.venv\Scripts\python -m pip install -e ".[dev]"; .venv\Scripts\python -m pytest tests/test_version.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```powershell
git add pyproject.toml src tests
git commit -m "chore: scaffold yt_launcher package"
```

---

### Task 2: 타일 모델

**Files:**
- Create: `src/yt_launcher/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: 없음
- Produces: `PALETTE: tuple[str, ...]` (8색), `auto_color(text: str) -> str`, `@dataclass Tile(query: str, name: str = "", color: str = "", id: str = <uuid hex>)` with `label: str` (property), `display_color: str` (property), `to_dict() -> dict`, `Tile.from_dict(data: dict) -> Tile` (빈/누락 query는 `ValueError`/`KeyError`).

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_models.py`

```python
import pytest

from yt_launcher.models import PALETTE, Tile, auto_color


def test_palette_has_eight_colors():
    assert len(PALETTE) == 8
    assert PALETTE[0] == "#E53935"


def test_label_falls_back_to_query():
    assert Tile(query="로파이 음악").label == "로파이 음악"
    assert Tile(query="로파이 음악", name="  ").label == "로파이 음악"
    assert Tile(query="로파이 음악", name="공부").label == "공부"


def test_auto_color_is_deterministic_and_in_palette():
    assert auto_color("lofi") == auto_color("lofi")
    assert auto_color("lofi") in PALETTE


def test_display_color_prefers_explicit_color():
    assert Tile(query="lofi", color="#123456").display_color == "#123456"
    assert Tile(query="lofi").display_color == auto_color("lofi")


def test_ids_are_unique():
    assert Tile(query="a").id != Tile(query="a").id


def test_dict_roundtrip():
    tile = Tile(query="뉴스", name="아침 뉴스", color=PALETTE[3])
    assert Tile.from_dict(tile.to_dict()) == tile


def test_from_dict_generates_missing_id():
    tile = Tile.from_dict({"query": "운동"})
    assert tile.query == "운동"
    assert tile.name == ""
    assert len(tile.id) == 32


def test_from_dict_rejects_empty_or_missing_query():
    with pytest.raises(ValueError):
        Tile.from_dict({"query": "   "})
    with pytest.raises(KeyError):
        Tile.from_dict({"name": "x"})
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.models'`

- [ ] **Step 3: 구현** — `src/yt_launcher/models.py`

```python
"""런처 타일 데이터."""

from __future__ import annotations

import uuid
import zlib
from dataclasses import asdict, dataclass, field

PALETTE = (
    "#E53935",
    "#D81B60",
    "#8E24AA",
    "#3949AB",
    "#1E88E5",
    "#00897B",
    "#43A047",
    "#F4511E",
)


def auto_color(text: str) -> str:
    """검색어마다 항상 같은 팔레트 색을 고른다."""
    return PALETTE[zlib.crc32(text.encode("utf-8")) % len(PALETTE)]


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class Tile:
    query: str
    name: str = ""
    color: str = ""
    id: str = field(default_factory=_new_id)

    @property
    def label(self) -> str:
        return self.name.strip() or self.query

    @property
    def display_color(self) -> str:
        return self.color or auto_color(self.query)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Tile:
        query = str(data["query"]).strip()
        if not query:
            raise ValueError("tile query is empty")
        return cls(
            query=query,
            name=str(data.get("name", "")),
            color=str(data.get("color", "")),
            id=str(data.get("id") or _new_id()),
        )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_models.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```powershell
git add src/yt_launcher/models.py tests/test_models.py
git commit -m "feat: add Tile model and color palette"
```

---

### Task 3: 창 위치 계산

**Files:**
- Create: `src/yt_launcher/geometry.py`
- Test: `tests/test_geometry.py`

**Interfaces:**
- Consumes: 없음
- Produces: `@dataclass(frozen=True) Rect(x: int, y: int, w: int, h: int)` with `intersection_area(other: Rect) -> int`; 상수 `DEFAULT_W = 360`, `DEFAULT_H = 480`, `MARGIN = 16`; `default_rect(work: Rect) -> Rect`; `is_visible_on_any(rect: Rect, works: list[Rect], min_ratio: float = 0.3) -> bool`.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_geometry.py`

```python
from yt_launcher.geometry import Rect, default_rect, is_visible_on_any


def test_default_rect_top_right_of_primary():
    assert default_rect(Rect(0, 0, 1920, 1040)) == Rect(1544, 16, 360, 480)


def test_default_rect_respects_work_area_offset():
    assert default_rect(Rect(1920, 0, 1280, 984)) == Rect(2824, 16, 360, 480)


def test_default_rect_shrinks_on_small_screens():
    assert default_rect(Rect(0, 0, 300, 400)) == Rect(16, 16, 268, 368)


def test_intersection_area():
    assert Rect(0, 0, 100, 100).intersection_area(Rect(50, 50, 100, 100)) == 2500
    assert Rect(0, 0, 100, 100).intersection_area(Rect(200, 0, 10, 10)) == 0


def test_visible_when_mostly_on_screen():
    works = [Rect(0, 0, 1920, 1080)]
    assert is_visible_on_any(Rect(100, 100, 360, 480), works)
    assert is_visible_on_any(Rect(1800, 0, 200, 100), works)  # 60% 겹침


def test_not_visible_when_off_screen_or_barely_overlapping():
    works = [Rect(0, 0, 1920, 1080)]
    assert not is_visible_on_any(Rect(5000, 0, 360, 480), works)
    assert not is_visible_on_any(Rect(1880, 0, 200, 100), works)  # 20% 겹침
    assert not is_visible_on_any(Rect(0, 0, 0, 0), works)


def test_visible_on_secondary_monitor():
    works = [Rect(0, 0, 1920, 1080), Rect(1920, 0, 1280, 1024)]
    assert is_visible_on_any(Rect(2500, 100, 360, 480), works)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_geometry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.geometry'`

- [ ] **Step 3: 구현** — `src/yt_launcher/geometry.py`

```python
"""런처 창 위치 계산 (Qt 비의존)."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_W = 360
DEFAULT_H = 480
MARGIN = 16


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    def intersection_area(self, other: Rect) -> int:
        width = min(self.x + self.w, other.x + other.w) - max(self.x, other.x)
        height = min(self.y + self.h, other.y + other.h) - max(self.y, other.y)
        return max(width, 0) * max(height, 0)


def default_rect(work: Rect) -> Rect:
    """작업 영역 우상단에 여백을 두고 기본 크기로 배치한다."""
    w = min(DEFAULT_W, work.w - 2 * MARGIN)
    h = min(DEFAULT_H, work.h - 2 * MARGIN)
    return Rect(work.x + work.w - w - MARGIN, work.y + MARGIN, w, h)


def is_visible_on_any(rect: Rect, works: list[Rect], min_ratio: float = 0.3) -> bool:
    """창 면적의 min_ratio 이상이 어느 한 작업 영역과 겹치면 True."""
    area = rect.w * rect.h
    if area <= 0:
        return False
    return any(rect.intersection_area(work) >= area * min_ratio for work in works)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_geometry.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```powershell
git add src/yt_launcher/geometry.py tests/test_geometry.py
git commit -m "feat: add window placement geometry"
```

---

### Task 4: 설정 저장소

**Files:**
- Create: `src/yt_launcher/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: `models.Tile` (`to_dict`, `from_dict`), `geometry.Rect`
- Produces: `@dataclass Config(tiles: list[Tile] = [], window: Rect | None = None, locked: bool = False, autostart: bool | None = None, last_run_version: str = "", notified_version: str = "", chrome_notice_shown: bool = False)`; `default_dir() -> Path` (`%APPDATA%\YT-Launcher`); `class Storage(directory: Path)` with `.path: Path`, `load() -> tuple[Config, bool]` (두 번째 값 = 손상 복구 여부), `save(config: Config) -> None`.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_storage.py`

```python
import json

from yt_launcher.geometry import Rect
from yt_launcher.models import Tile
from yt_launcher.storage import Config, Storage, default_dir


def test_default_dir_under_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_dir() == tmp_path / "YT-Launcher"


def test_missing_file_returns_defaults(tmp_path):
    config, recovered = Storage(tmp_path).load()
    assert config == Config()
    assert recovered is False


def test_roundtrip(tmp_path):
    storage = Storage(tmp_path / "nested")
    config = Config(
        tiles=[Tile(query="로파이 음악"), Tile(query="뉴스", name="아침", color="#1E88E5")],
        window=Rect(10, 20, 360, 480),
        locked=True,
        autostart=False,
        last_run_version="0.1.0",
        notified_version="0.2.0",
        chrome_notice_shown=True,
    )
    storage.save(config)
    loaded, recovered = storage.load()
    assert loaded == config
    assert recovered is False


def test_save_is_utf8_and_leaves_no_temp_file(tmp_path):
    storage = Storage(tmp_path)
    storage.save(Config(tiles=[Tile(query="로파이")]))
    text = storage.path.read_text(encoding="utf-8")
    assert "로파이" in text
    assert json.loads(text)["schema"] == 1
    assert [p.name for p in tmp_path.iterdir()] == ["config.json"]


def test_corrupt_json_is_backed_up(tmp_path):
    storage = Storage(tmp_path)
    storage.path.write_text("{not json", encoding="utf-8")
    config, recovered = storage.load()
    assert config == Config()
    assert recovered is True
    assert (tmp_path / "config.json.bak").read_text(encoding="utf-8") == "{not json"
    assert not storage.path.exists()


def test_invalid_structure_is_backed_up(tmp_path):
    storage = Storage(tmp_path)
    storage.path.write_text(json.dumps({"tiles": [{"name": "x"}]}), encoding="utf-8")
    config, recovered = storage.load()
    assert config == Config()
    assert recovered is True
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.storage'`

- [ ] **Step 3: 구현** — `src/yt_launcher/storage.py`

```python
"""설정 파일(config.json) 읽기·쓰기."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .geometry import Rect
from .models import Tile

log = logging.getLogger(__name__)

SCHEMA = 1
CONFIG_NAME = "config.json"


@dataclass
class Config:
    tiles: list[Tile] = field(default_factory=list)
    window: Rect | None = None
    locked: bool = False
    autostart: bool | None = None
    last_run_version: str = ""
    notified_version: str = ""
    chrome_notice_shown: bool = False


def default_dir() -> Path:
    return Path(os.environ.get("APPDATA") or Path.home()) / "YT-Launcher"


def config_to_dict(config: Config) -> dict:
    return {
        "schema": SCHEMA,
        "tiles": [tile.to_dict() for tile in config.tiles],
        "window": asdict(config.window) if config.window else None,
        "locked": config.locked,
        "autostart": config.autostart,
        "last_run_version": config.last_run_version,
        "notified_version": config.notified_version,
        "chrome_notice_shown": config.chrome_notice_shown,
    }


def config_from_dict(data: object) -> Config:
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    window = data.get("window")
    autostart = data.get("autostart")
    return Config(
        tiles=[Tile.from_dict(item) for item in data.get("tiles", [])],
        window=Rect(int(window["x"]), int(window["y"]), int(window["w"]), int(window["h"]))
        if window
        else None,
        locked=bool(data.get("locked", False)),
        autostart=None if autostart is None else bool(autostart),
        last_run_version=str(data.get("last_run_version", "")),
        notified_version=str(data.get("notified_version", "")),
        chrome_notice_shown=bool(data.get("chrome_notice_shown", False)),
    )


class Storage:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.path = self.directory / CONFIG_NAME

    def load(self) -> tuple[Config, bool]:
        """설정을 읽는다. 손상된 파일은 .bak으로 옮기고 (기본 설정, True)를 돌려준다."""
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return Config(), False
        try:
            return config_from_dict(json.loads(raw)), False
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            log.warning("설정 파일 손상, 백업 후 초기화: %s", exc)
            os.replace(self.path, self.path.with_name(CONFIG_NAME + ".bak"))
            return Config(), True

    def save(self, config: Config) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(CONFIG_NAME + ".tmp")
        tmp.write_text(
            json.dumps(config_to_dict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_storage.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```powershell
git add src/yt_launcher/storage.py tests/test_storage.py
git commit -m "feat: add atomic config storage with corruption recovery"
```

---

### Task 5: Win32 래퍼

**Files:**
- Create: `src/yt_launcher/win32.py`
- Test: `tests/test_win32.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `is_chrome_exe(path: str) -> bool`
  - `list_chrome_windows() -> list[tuple[int, str]]` — 보이는 `Chrome_WidgetWin_1` 창 중 프로세스가 `chrome.exe`인 것 (Z순서, 위가 먼저), `(hwnd, title)`
  - `maximize_and_focus(hwnd: int) -> bool`
  - `focus_chrome_window(timeout: float = 5.0, settle: float = 0.5, poll: float = 0.1) -> bool`
  - `allow_any_foreground() -> None`
  - `send_to_bottom(hwnd: int) -> None`
  - `pin_to_desktop(hwnd: int) -> bool` — 소유자를 `Progman`으로 지정 (Win+D 대응)
  - `create_mutex(name: str) -> int | None`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_win32.py`

```python
from yt_launcher import win32


def test_is_chrome_exe():
    assert win32.is_chrome_exe(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    assert win32.is_chrome_exe(r"C:\X\CHROME.EXE")
    assert not win32.is_chrome_exe(r"C:\Program Files\Microsoft VS Code\Code.exe")
    assert not win32.is_chrome_exe("")


def test_list_chrome_windows_returns_pairs():
    windows = win32.list_chrome_windows()
    assert isinstance(windows, list)
    for hwnd, title in windows:
        assert isinstance(hwnd, int)
        assert title


def test_create_mutex_returns_handle():
    assert win32.create_mutex("YTLauncherTestMutex") is not None


def test_bottom_and_pin_ignore_invalid_window():
    win32.send_to_bottom(0)  # 잘못된 핸들이어도 예외 없음
    assert win32.pin_to_desktop(0) is False
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_win32.py -v`
Expected: FAIL — `ImportError: cannot import name 'win32'`

- [ ] **Step 3: 구현** — `src/yt_launcher/win32.py`

```python
"""Win32 API 래퍼 (ctypes). 실패해도 예외 대신 False/None을 돌려준다."""

from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes
from pathlib import Path

log = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SW_MAXIMIZE = 3
HWND_BOTTOM = wintypes.HWND(1)
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
GWLP_HWNDPARENT = -8
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ASFW_ANY = 0xFFFFFFFF
CHROME_CLASS = "Chrome_WidgetWin_1"

LONG_PTR = ctypes.c_ssize_t
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
user32.AllowSetForegroundWindow.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
user32.SetWindowLongPtrW.restype = LONG_PTR
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE


def is_chrome_exe(path: str) -> bool:
    return bool(path) and Path(path).name.lower() == "chrome.exe"


def _class_name(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _window_text(hwnd) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _process_image(hwnd) -> str:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def list_chrome_windows() -> list[tuple[int, str]]:
    """보이는 크롬 최상위 창을 Z순서(위가 먼저)로 돌려준다."""
    found: list[tuple[int, str]] = []

    @WNDENUMPROC
    def callback(hwnd, _lparam):
        if hwnd and user32.IsWindowVisible(hwnd) and _class_name(hwnd) == CHROME_CLASS:
            title = _window_text(hwnd)
            if title and is_chrome_exe(_process_image(hwnd)):
                found.append((int(hwnd), title))
        return True

    user32.EnumWindows(callback, 0)
    return found


def maximize_and_focus(hwnd: int) -> bool:
    user32.ShowWindow(hwnd, SW_MAXIMIZE)
    if user32.SetForegroundWindow(hwnd):
        return True
    foreground = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
    current = kernel32.GetCurrentThreadId()
    attached = bool(fg_thread and fg_thread != current and user32.AttachThreadInput(current, fg_thread, True))
    try:
        user32.BringWindowToTop(hwnd)
        return bool(user32.SetForegroundWindow(hwnd))
    finally:
        if attached:
            user32.AttachThreadInput(current, fg_thread, False)


def focus_chrome_window(timeout: float = 5.0, settle: float = 0.5, poll: float = 0.1) -> bool:
    """방금 연 유튜브 탭의 크롬 창을 찾아 최대화하고 전면으로 가져온다."""
    time.sleep(settle)
    deadline = time.monotonic() + timeout
    while True:
        windows = list_chrome_windows()
        target = next((hwnd for hwnd, title in windows if "YouTube" in title), None)
        if target is not None or time.monotonic() >= deadline:
            break
        time.sleep(poll)
    if target is None and windows:
        target = windows[0][0]
    if target is None:
        log.warning("크롬 창을 찾지 못했습니다")
        return False
    return maximize_and_focus(target)


def allow_any_foreground() -> None:
    user32.AllowSetForegroundWindow(ASFW_ANY)


def send_to_bottom(hwnd: int) -> None:
    user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)


def pin_to_desktop(hwnd: int) -> bool:
    """창의 소유자를 바탕화면(Progman)으로 지정해 Win+D에도 남도록 한다."""
    progman = user32.FindWindowW("Progman", None)
    if not progman or not hwnd:
        return False
    user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, progman)
    return True


def create_mutex(name: str) -> int | None:
    handle = kernel32.CreateMutexW(None, False, name)
    return int(handle) if handle else None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_win32.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```powershell
git add src/yt_launcher/win32.py tests/test_win32.py
git commit -m "feat: add Win32 helpers for chrome focus and desktop layering"
```

---

### Task 6: 크롬 실행

**Files:**
- Create: `src/yt_launcher/chrome.py`
- Test: `tests/test_chrome.py`

**Interfaces:**
- Consumes: `win32.focus_chrome_window()`, `win32.allow_any_foreground()`
- Produces: `SEARCH_URL`, `build_search_url(query: str) -> str`, `registry_chrome_path() -> Path | None`, `candidate_paths(env: Mapping[str, str]) -> list[Path]`, `find_chrome(registry_lookup=registry_chrome_path, env=None) -> Path | None`, `open_search(query: str, chrome_path: Path | None, *, popen=..., focus=..., browser_open=..., allow_foreground=...) -> bool` (크롬으로 열었으면 True, 기본 브라우저 폴백이면 False).

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_chrome.py`

```python
from pathlib import Path

from yt_launcher import chrome


def test_build_search_url_encodes_korean_and_specials():
    assert chrome.build_search_url("로파이 음악") == (
        "https://www.youtube.com/results?search_query="
        "%EB%A1%9C%ED%8C%8C%EC%9D%B4+%EC%9D%8C%EC%95%85"
    )
    assert chrome.build_search_url("lofi & chill #1").endswith("lofi+%26+chill+%231")
    assert chrome.build_search_url("  a b  ").endswith("=a+b")


def test_find_chrome_prefers_registry(tmp_path):
    exe = tmp_path / "chrome.exe"
    exe.write_bytes(b"")
    assert chrome.find_chrome(registry_lookup=lambda: exe, env={}) == exe


def test_find_chrome_falls_back_to_known_paths(tmp_path):
    local = tmp_path / "local"
    exe = local / "Google" / "Chrome" / "Application" / "chrome.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    env = {"PROGRAMFILES": str(tmp_path / "pf"), "LOCALAPPDATA": str(local)}
    assert chrome.find_chrome(registry_lookup=lambda: None, env=env) == exe


def test_find_chrome_returns_none_when_missing(tmp_path):
    env = {"PROGRAMFILES": str(tmp_path)}
    assert chrome.find_chrome(registry_lookup=lambda: None, env=env) is None


def test_registry_lookup_does_not_crash():
    result = chrome.registry_chrome_path()
    assert result is None or result.is_file()


def test_open_search_launches_chrome_and_focuses():
    calls = []
    used = chrome.open_search(
        "lofi",
        Path(r"C:\chrome.exe"),
        popen=lambda args, **kw: calls.append(("popen", args)),
        focus=lambda: calls.append(("focus",)),
        browser_open=lambda url: calls.append(("browser", url)),
        allow_foreground=lambda: calls.append(("allow",)),
    )
    assert used is True
    assert calls == [
        ("allow",),
        ("popen", [r"C:\chrome.exe", "https://www.youtube.com/results?search_query=lofi"]),
        ("focus",),
    ]


def test_open_search_falls_back_to_default_browser():
    calls = []
    used = chrome.open_search(
        "lofi",
        None,
        popen=lambda args, **kw: calls.append("popen"),
        focus=lambda: calls.append("focus"),
        browser_open=lambda url: calls.append(url),
        allow_foreground=lambda: calls.append("allow"),
    )
    assert used is False
    assert calls == ["https://www.youtube.com/results?search_query=lofi"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_chrome.py -v`
Expected: FAIL — `ImportError: cannot import name 'chrome'`

- [ ] **Step 3: 구현** — `src/yt_launcher/chrome.py`

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_chrome.py -v`
Expected: 7 passed

- [ ] **Step 5: 실제 동작 확인 (수동, 1회)**

Run: `.venv\Scripts\python -c "from yt_launcher import chrome; print(chrome.open_search('로파이 음악', chrome.find_chrome()))"`
Expected: `True` 출력, 크롬이 최대화된 창(F11 아님)으로 유튜브 "로파이 음악" 검색 결과를 연다. 크롬이 켜진 상태/꺼진 상태 각각 한 번씩 확인.

- [ ] **Step 6: Commit**

```powershell
git add src/yt_launcher/chrome.py tests/test_chrome.py
git commit -m "feat: open YouTube search in maximized Chrome"
```

---

### Task 7: 윈도우 시작 시 자동 실행

**Files:**
- Create: `src/yt_launcher/autostart.py`
- Test: `tests/test_autostart.py`

**Interfaces:**
- Consumes: 없음
- Produces: `RUN_KEY`, `VALUE_NAME = "YTLauncher"`, `class RunKeyBackend(value_name: str = VALUE_NAME)` with `get() -> str | None`, `set(value: str) -> None`, `delete() -> None`; `launch_command() -> str` (frozen이면 `"<exe>"`, 개발 중이면 `"<pythonw>" -m yt_launcher`); `class AutoStart(backend=None)` with `is_enabled() -> bool`, `enable(command: str | None = None) -> None`, `disable() -> None`. 테스트용 백엔드는 `get/set/delete`만 있으면 된다.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_autostart.py`

```python
import sys

from yt_launcher.autostart import AutoStart, RunKeyBackend, launch_command


class FakeBackend:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def delete(self):
        self.value = None


def test_enable_disable_with_fake_backend():
    backend = FakeBackend()
    autostart = AutoStart(backend)
    assert not autostart.is_enabled()
    autostart.enable('"C:\\app\\YTLauncher.exe"')
    assert autostart.is_enabled()
    assert backend.value == '"C:\\app\\YTLauncher.exe"'
    autostart.disable()
    assert not autostart.is_enabled()


def test_launch_command_in_dev_uses_pythonw(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    command = launch_command()
    assert command.endswith('pythonw.exe" -m yt_launcher')


def test_launch_command_when_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\YT-Launcher\YTLauncher.exe")
    assert launch_command() == '"C:\\Apps\\YT-Launcher\\YTLauncher.exe"'


def test_real_run_key_roundtrip():
    backend = RunKeyBackend(value_name="YTLauncherPytest")
    try:
        backend.set('"C:\\nonexistent\\yt-launcher-test.exe"')
        assert backend.get() == '"C:\\nonexistent\\yt-launcher-test.exe"'
    finally:
        backend.delete()
    assert backend.get() is None
    backend.delete()  # 없는 값 삭제도 예외 없음
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_autostart.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.autostart'`

- [ ] **Step 3: 구현** — `src/yt_launcher/autostart.py`

```python
"""HKCU Run 키로 윈도우 시작 시 자동 실행을 켜고 끈다."""

from __future__ import annotations

import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "YTLauncher"


class RunKeyBackend:
    def __init__(self, value_name: str = VALUE_NAME):
        self.value_name = value_name

    def get(self) -> str | None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _ = winreg.QueryValueEx(key, self.value_name)
        except FileNotFoundError:
            return None
        return str(value)

    def set(self, value: str) -> None:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.value_name, 0, winreg.REG_SZ, value)

    def delete(self) -> None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, self.value_name)
        except FileNotFoundError:
            pass


def launch_command() -> str:
    """Run 키에 등록할 실행 명령."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return f'"{pythonw}" -m yt_launcher'


class AutoStart:
    def __init__(self, backend=None):
        self.backend = backend or RunKeyBackend()

    def is_enabled(self) -> bool:
        return self.backend.get() is not None

    def enable(self, command: str | None = None) -> None:
        self.backend.set(command or launch_command())

    def disable(self) -> None:
        self.backend.delete()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_autostart.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```powershell
git add src/yt_launcher/autostart.py tests/test_autostart.py
git commit -m "feat: add autostart via HKCU Run key"
```

---

### Task 8: 업데이트 확인·다운로드·검증

**Files:**
- Create: `src/yt_launcher/updater.py`
- Test: `tests/test_updater.py`

**Interfaces:**
- Consumes: `version.REPO`, `version.__version__`
- Produces:
  - `class UpdateError(Exception)`
  - `@dataclass(frozen=True) Asset(name: str, url: str, size: int)`
  - `@dataclass(frozen=True) Release(tag: str, version: str, html_url: str, installer: Asset | None, sums: Asset | None)`
  - `parse_release(data: dict) -> Release | None` (draft/prerelease/태그 없음 → None)
  - `is_newer(candidate: str, current: str) -> bool`
  - `fetch_latest(repo: str = REPO, opener=urlopen) -> Release | None` (404 → None, 그 외 네트워크/파싱 오류 → `UpdateError`)
  - `parse_sums(text: str) -> dict[str, str]`, `sha256_file(path: Path) -> str`
  - `download(asset: Asset, dest: Path, progress=None, opener=urlopen) -> Path`
  - `download_and_verify(release: Release, dest_dir: Path, progress=None, opener=urlopen) -> Path`
  - `launch_installer(path: Path, popen=subprocess.Popen) -> None`
  - `SILENT_ARGS = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]`
  - `opener` 시그니처: `opener(request: urllib.request.Request, timeout=...) -> 컨텍스트 매니저 응답(.read(n))`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_updater.py`

```python
import hashlib
import io
import json
import subprocess
from urllib.error import HTTPError, URLError

import pytest

from yt_launcher import updater
from yt_launcher.updater import Asset, Release, UpdateError

INSTALLER = b"installer-bytes"
INSTALLER_SHA = "204676736cea68d6411da9d3aa3fab0a5e70b023ba30cd560cfa9c8e7250f4df"


def release_json(**overrides):
    data = {
        "tag_name": "v0.2.0",
        "html_url": "https://github.com/ssenu/YT-launcher/releases/tag/v0.2.0",
        "draft": False,
        "prerelease": False,
        "assets": [
            {"name": "YT-Launcher-Setup-0.2.0.exe", "browser_download_url": "https://dl/setup.exe", "size": len(INSTALLER)},
            {"name": "SHA256SUMS.txt", "browser_download_url": "https://dl/sums.txt", "size": 100},
            {"name": "source.zip", "browser_download_url": "https://dl/src.zip", "size": 5},
        ],
    }
    data.update(overrides)
    return data


class FakeOpener:
    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        result = self.responses[request.full_url]
        if isinstance(result, Exception):
            raise result
        return io.BytesIO(result)


def test_parse_release_picks_assets():
    release = updater.parse_release(release_json())
    assert release.tag == "v0.2.0"
    assert release.version == "0.2.0"
    assert release.installer == Asset("YT-Launcher-Setup-0.2.0.exe", "https://dl/setup.exe", len(INSTALLER))
    assert release.sums.name == "SHA256SUMS.txt"


def test_parse_release_skips_draft_and_prerelease():
    assert updater.parse_release(release_json(draft=True)) is None
    assert updater.parse_release(release_json(prerelease=True)) is None
    assert updater.parse_release(release_json(tag_name="")) is None


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("v0.2.0", "0.1.0", True),
        ("0.1.0", "0.1.0", False),
        ("v0.1.0", "0.2.0", False),
        ("v0.10.0", "0.9.0", True),
        ("garbage", "0.1.0", False),
    ],
)
def test_is_newer(candidate, current, expected):
    assert updater.is_newer(candidate, current) is expected


def test_fetch_latest_parses_and_sends_headers():
    url = "https://api.github.com/repos/ssenu/YT-launcher/releases/latest"
    opener = FakeOpener({url: json.dumps(release_json()).encode()})
    release = updater.fetch_latest("ssenu/YT-launcher", opener=opener)
    assert release.version == "0.2.0"
    assert opener.requests[0].get_header("User-agent").startswith("YT-Launcher/")


def test_fetch_latest_404_means_no_release():
    url = "https://api.github.com/repos/ssenu/YT-launcher/releases/latest"
    opener = FakeOpener({url: HTTPError(url, 404, "Not Found", None, None)})
    assert updater.fetch_latest("ssenu/YT-launcher", opener=opener) is None


def test_fetch_latest_network_error_raises():
    url = "https://api.github.com/repos/ssenu/YT-launcher/releases/latest"
    opener = FakeOpener({url: URLError("offline")})
    with pytest.raises(UpdateError):
        updater.fetch_latest("ssenu/YT-launcher", opener=opener)


def test_parse_sums():
    text = f"{INSTALLER_SHA.upper()}  YT-Launcher-Setup-0.2.0.exe\nabc *other.exe\n\n"
    assert updater.parse_sums(text) == {
        "YT-Launcher-Setup-0.2.0.exe": INSTALLER_SHA,
        "other.exe": "abc",
    }


def test_sha256_file(tmp_path):
    path = tmp_path / "f"
    path.write_bytes(INSTALLER)
    assert updater.sha256_file(path) == hashlib.sha256(INSTALLER).hexdigest() == INSTALLER_SHA


def test_download_and_verify_success(tmp_path):
    release = updater.parse_release(release_json())
    opener = FakeOpener({
        "https://dl/sums.txt": f"{INSTALLER_SHA}  YT-Launcher-Setup-0.2.0.exe\n".encode(),
        "https://dl/setup.exe": INSTALLER,
    })
    progress = []
    path = updater.download_and_verify(release, tmp_path, progress=lambda d, t: progress.append((d, t)), opener=opener)
    assert path == tmp_path / "YT-Launcher-Setup-0.2.0.exe"
    assert path.read_bytes() == INSTALLER
    assert progress[-1] == (len(INSTALLER), len(INSTALLER))
    assert not list(tmp_path.glob("*.part"))


def test_download_and_verify_hash_mismatch(tmp_path):
    release = updater.parse_release(release_json())
    opener = FakeOpener({
        "https://dl/sums.txt": f"{'0' * 64}  YT-Launcher-Setup-0.2.0.exe\n".encode(),
        "https://dl/setup.exe": INSTALLER,
    })
    with pytest.raises(UpdateError):
        updater.download_and_verify(release, tmp_path, opener=opener)
    assert not (tmp_path / "YT-Launcher-Setup-0.2.0.exe").exists()


def test_download_and_verify_requires_assets(tmp_path):
    release = Release("v0.2.0", "0.2.0", "", None, None)
    with pytest.raises(UpdateError):
        updater.download_and_verify(release, tmp_path, opener=FakeOpener({}))


def test_download_network_error_cleans_partial(tmp_path):
    asset = Asset("YT-Launcher-Setup-0.2.0.exe", "https://dl/setup.exe", 10)
    opener = FakeOpener({"https://dl/setup.exe": URLError("offline")})
    with pytest.raises(UpdateError):
        updater.download(asset, tmp_path / asset.name, opener=opener)
    assert list(tmp_path.iterdir()) == []


def test_launch_installer_runs_silently(tmp_path):
    calls = []
    updater.launch_installer(tmp_path / "setup.exe", popen=lambda args, **kw: calls.append((args, kw)))
    args, kwargs = calls[0]
    assert args == [str(tmp_path / "setup.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
    assert kwargs["creationflags"] & subprocess.DETACHED_PROCESS
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_updater.py -v`
Expected: FAIL — `ImportError: cannot import name 'updater'`

- [ ] **Step 3: 구현** — `src/yt_launcher/updater.py`

```python
"""GitHub Releases 기반 업데이트 확인·다운로드·설치 실행."""

from __future__ import annotations

import hashlib
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
    except (OSError, ValueError) as exc:
        raise UpdateError(f"릴리스 정보를 가져오지 못했습니다: {exc}") from exc
    return parse_release(data) if isinstance(data, dict) else None


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


def download(asset: Asset, dest: Path, progress: Progress | None = None, opener=urlopen) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    done = 0
    try:
        with opener(_request(asset.url, "application/octet-stream"), timeout=TIMEOUT) as response, open(
            partial, "wb"
        ) as out:
            while chunk := response.read(CHUNK):
                out.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, asset.size)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise UpdateError(f"다운로드 실패: {exc}") from exc
    os.replace(partial, dest)
    return dest


def download_and_verify(
    release: Release, dest_dir: Path, progress: Progress | None = None, opener=urlopen
) -> Path:
    if release.installer is None or release.sums is None:
        raise UpdateError("릴리스에 설치 파일 또는 SHA256SUMS.txt가 없습니다.")
    sums_path = download(release.sums, dest_dir / SUMS_NAME, opener=opener)
    expected = parse_sums(sums_path.read_text(encoding="utf-8-sig")).get(release.installer.name)
    if not expected:
        raise UpdateError("SHA256SUMS.txt에 설치 파일 해시가 없습니다.")
    installer_path = download(release.installer, dest_dir / release.installer.name, progress, opener)
    if sha256_file(installer_path) != expected:
        installer_path.unlink(missing_ok=True)
        raise UpdateError("설치 파일 해시가 일치하지 않습니다.")
    return installer_path


def launch_installer(path: Path, popen=subprocess.Popen) -> None:
    """설치 프로그램을 조용한 모드로 분리 실행한다. 호출 후 앱은 곧바로 종료해야 한다."""
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    popen([str(path), *SILENT_ARGS], creationflags=flags, close_fds=True)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_updater.py -v`
Expected: 17 passed

- [ ] **Step 5: Commit**

```powershell
git add src/yt_launcher/updater.py tests/test_updater.py
git commit -m "feat: add GitHub release update check, download and verify"
```

---

### Task 9: 아이콘 리소스

**Files:**
- Create: `tools/make_icon.py`, `src/yt_launcher/resources.py`, `src/yt_launcher/assets/icon.png`, `src/yt_launcher/assets/icon.ico` (생성물, 커밋함)
- Test: `tests/test_resources.py`

**Interfaces:**
- Consumes: 없음
- Produces: `resources.ASSETS_DIR: Path`, `asset_path(name: str) -> Path`, `app_icon() -> QIcon` (QApplication 생성 후 호출)

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_resources.py`

```python
from yt_launcher.resources import app_icon, asset_path


def test_icon_files_exist():
    assert asset_path("icon.png").is_file()
    ico = asset_path("icon.ico").read_bytes()
    assert ico[:4] == b"\x00\x00\x01\x00"


def test_app_icon_loads(qapp):
    assert not app_icon().isNull()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_resources.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.resources'`

- [ ] **Step 3: 아이콘 생성 스크립트 작성** — `tools/make_icon.py`

```python
"""src/yt_launcher/assets/icon.png 와 icon.ico 를 생성한다 (빨간 재생 버튼).

실행: .venv\\Scripts\\python tools\\make_icon.py
"""

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPolygonF

ASSETS = Path(__file__).resolve().parents[1] / "src" / "yt_launcher" / "assets"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def render(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#E53935"))
    margin = size * 0.06
    painter.drawRoundedRect(QRectF(margin, size * 0.18, size - 2 * margin, size * 0.64), size * 0.16, size * 0.16)
    painter.setBrush(QColor("#FFFFFF"))
    c = size / 2
    painter.drawPolygon(
        QPolygonF([
            QPointF(c - size * 0.12, c - size * 0.16),
            QPointF(c - size * 0.12, c + size * 0.16),
            QPointF(c + size * 0.17, c),
        ])
    )
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data.data())


def build_ico(images: list[tuple[int, bytes]]) -> bytes:
    """PNG 데이터를 담은 ICO 컨테이너 (Windows Vista+)."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    payload = b""
    for size, png in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(payload))
        payload += png
    return header + entries + payload


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    ASSETS.mkdir(parents=True, exist_ok=True)
    render(256).save(str(ASSETS / "icon.png"), "PNG")
    (ASSETS / "icon.ico").write_bytes(build_ico([(s, png_bytes(render(s))) for s in ICO_SIZES]))
    print(f"written: {ASSETS}")
    del app


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 아이콘 생성**

Run: `.venv\Scripts\python tools\make_icon.py`
Expected: `written: ...\src\yt_launcher\assets` 출력, `icon.png`(256×256)와 `icon.ico` 생성.

- [ ] **Step 5: 리소스 모듈 작성** — `src/yt_launcher/resources.py`

```python
"""패키지에 포함된 이미지 리소스."""

from pathlib import Path

from PySide6.QtGui import QIcon

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def asset_path(name: str) -> Path:
    return ASSETS_DIR / name


def app_icon() -> QIcon:
    return QIcon(str(asset_path("icon.png")))
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_resources.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```powershell
git add tools/make_icon.py src/yt_launcher/resources.py src/yt_launcher/assets tests/test_resources.py
git commit -m "feat: add app icon and resource helpers"
```

---

### Task 10: 타일 그리드

**Files:**
- Create: `src/yt_launcher/ui/__init__.py`, `src/yt_launcher/ui/tile_grid.py`
- Test: `tests/test_tile_grid.py`

**Interfaces:**
- Consumes: `models.Tile` (`id`, `label`, `display_color`, `query`)
- Produces: `ADD_ID = "__add__"`, `ID_ROLE`, `COLOR_ROLE`, `TILE_SIZE = QSize(100, 68)`; `class TileGrid(QListWidget)` with signals `tile_clicked(str)`, `add_requested()`, `edit_requested(str)`, `delete_requested(str)`, `order_changed(list)`; methods `set_tiles(tiles: list[Tile]) -> None`, `tile_ids() -> list[str]`, `_keep_add_last() -> None`.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_tile_grid.py`

```python
from yt_launcher.models import Tile
from yt_launcher.ui.tile_grid import ADD_ID, ID_ROLE, TileGrid


def test_set_tiles_puts_add_button_last(qapp):
    grid = TileGrid()
    a, b = Tile(query="a"), Tile(query="b", name="비")
    grid.set_tiles([a, b])
    assert grid.count() == 3
    assert grid.item(0).text() == "a"
    assert grid.item(1).text() == "비"
    assert grid.item(2).data(ID_ROLE) == ADD_ID
    assert grid.tile_ids() == [a.id, b.id]


def test_set_tiles_replaces_previous_items(qapp):
    grid = TileGrid()
    grid.set_tiles([Tile(query="a"), Tile(query="b")])
    grid.set_tiles([Tile(query="c")])
    assert grid.count() == 2


def test_click_emits_tile_or_add(qapp):
    grid = TileGrid()
    tile = Tile(query="a")
    grid.set_tiles([tile])
    clicked, added = [], []
    grid.tile_clicked.connect(clicked.append)
    grid.add_requested.connect(lambda: added.append(True))
    grid.itemClicked.emit(grid.item(0))
    grid.itemClicked.emit(grid.item(1))
    assert clicked == [tile.id]
    assert added == [True]


def test_keep_add_last_after_reorder(qapp):
    grid = TileGrid()
    a, b = Tile(query="a"), Tile(query="b")
    grid.set_tiles([a, b])
    grid.insertItem(0, grid.takeItem(grid.count() - 1))
    grid._keep_add_last()
    assert grid.item(grid.count() - 1).data(ID_ROLE) == ADD_ID
    assert grid.tile_ids() == [a.id, b.id]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_tile_grid.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.ui'`

- [ ] **Step 3: 구현**

`src/yt_launcher/ui/__init__.py`:

```python
"""PySide6 화면 구성 요소."""
```

`src/yt_launcher/ui/tile_grid.py`:

```python
"""타일 그리드: 창 너비에 맞춰 줄바꿈되고 드래그로 순서를 바꾼다."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QStyle,
    QStyledItemDelegate,
)

from ..models import Tile

ADD_ID = "__add__"
ADD_COLOR = "#2B2F3A"
ID_ROLE = Qt.UserRole
COLOR_ROLE = Qt.UserRole + 1
TILE_SIZE = QSize(100, 68)
TILE_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled


class TileDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect).adjusted(3, 3, -3, -3)
        color = QColor(index.data(COLOR_ROLE))
        if option.state & QStyle.StateFlag.State_MouseOver:
            color = color.lighter(120)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 10, 10)

        font = QFont(option.font)
        font.setBold(True)
        if index.data(ID_ROLE) == ADD_ID:
            font.setPointSizeF(max(font.pointSizeF(), 9.0) + 8)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
        painter.drawText(rect.adjusted(6, 4, -6, -4), flags, index.data(Qt.DisplayRole))
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return TILE_SIZE


class TileGrid(QListWidget):
    tile_clicked = Signal(str)
    add_requested = Signal()
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    order_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ListMode)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(True)
        self.setSpacing(2)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setItemDelegate(TileDelegate(self))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemClicked.connect(self._on_item_clicked)

    def set_tiles(self, tiles: list[Tile]) -> None:
        self.clear()
        for tile in tiles:
            item = QListWidgetItem(tile.label)
            item.setData(ID_ROLE, tile.id)
            item.setData(COLOR_ROLE, tile.display_color)
            item.setToolTip(tile.query)
            item.setFlags(TILE_FLAGS)
            item.setSizeHint(TILE_SIZE)
            self.addItem(item)
        add = QListWidgetItem("＋")
        add.setData(ID_ROLE, ADD_ID)
        add.setData(COLOR_ROLE, ADD_COLOR)
        add.setToolTip("검색어 추가")
        add.setFlags(Qt.ItemIsEnabled)
        add.setSizeHint(TILE_SIZE)
        self.addItem(add)

    def tile_ids(self) -> list[str]:
        ids = (self.item(i).data(ID_ROLE) for i in range(self.count()))
        return [tile_id for tile_id in ids if tile_id != ADD_ID]

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self._keep_add_last()
        self.order_changed.emit(self.tile_ids())

    def _keep_add_last(self) -> None:
        for i in range(self.count()):
            if self.item(i).data(ID_ROLE) == ADD_ID and i != self.count() - 1:
                self.addItem(self.takeItem(i))
                return

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        tile_id = item.data(ID_ROLE)
        if tile_id == ADD_ID:
            self.add_requested.emit()
        else:
            self.tile_clicked.emit(tile_id)

    def _show_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if item is None or item.data(ID_ROLE) == ADD_ID:
            return
        tile_id = item.data(ID_ROLE)
        menu = QMenu(self)
        edit = menu.addAction("수정")
        delete = menu.addAction("삭제")
        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if chosen is edit:
            self.edit_requested.emit(tile_id)
        elif chosen is delete:
            self.delete_requested.emit(tile_id)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_tile_grid.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```powershell
git add src/yt_launcher/ui tests/test_tile_grid.py
git commit -m "feat: add reorderable tile grid"
```

---

### Task 11: 타일 추가·수정 대화상자

**Files:**
- Create: `src/yt_launcher/ui/tile_dialog.py`
- Test: `tests/test_tile_dialog.py`

**Interfaces:**
- Consumes: `models.Tile`, `models.PALETTE`
- Produces: `class TileDialog(QDialog)(parent=None, tile: Tile | None = None)` with attributes `query_edit: QLineEdit`, `name_edit: QLineEdit`, `ok_button: QPushButton`, `auto_button: QToolButton`, `color_buttons: dict[str, QToolButton]`; methods `selected_color() -> str` (자동이면 ""), `result_tile() -> Tile` (수정 시 원래 id 유지).

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_tile_dialog.py`

```python
from yt_launcher.models import PALETTE, Tile
from yt_launcher.ui.tile_dialog import TileDialog


def test_new_tile_requires_query(qapp):
    dialog = TileDialog()
    assert dialog.windowTitle() == "타일 추가"
    assert not dialog.ok_button.isEnabled()
    dialog.query_edit.setText("   ")
    assert not dialog.ok_button.isEnabled()
    dialog.query_edit.setText("  로파이 음악 ")
    assert dialog.ok_button.isEnabled()
    tile = dialog.result_tile()
    assert tile.query == "로파이 음악"
    assert tile.name == ""
    assert tile.color == ""


def test_pick_palette_color(qapp):
    dialog = TileDialog()
    dialog.query_edit.setText("뉴스")
    dialog.color_buttons[PALETTE[2]].click()
    assert dialog.selected_color() == PALETTE[2]
    dialog.auto_button.click()
    assert dialog.selected_color() == ""


def test_edit_prefills_and_keeps_id(qapp):
    tile = Tile(query="a", name="A", color=PALETTE[0])
    dialog = TileDialog(tile=tile)
    assert dialog.windowTitle() == "타일 수정"
    assert dialog.query_edit.text() == "a"
    assert dialog.name_edit.text() == "A"
    assert dialog.selected_color() == PALETTE[0]
    dialog.name_edit.setText(" B ")
    result = dialog.result_tile()
    assert result.id == tile.id
    assert result.name == "B"
    assert result.color == PALETTE[0]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_tile_dialog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.ui.tile_dialog'`

- [ ] **Step 3: 구현** — `src/yt_launcher/ui/tile_dialog.py`

```python
"""타일 추가·수정 대화상자."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
)

from ..models import PALETTE, Tile


class TileDialog(QDialog):
    def __init__(self, parent=None, tile: Tile | None = None):
        super().__init__(parent)
        self._tile = tile
        self.setWindowTitle("타일 수정" if tile else "타일 추가")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(340)

        self.query_edit = QLineEdit(tile.query if tile else "")
        self.query_edit.setPlaceholderText("유튜브에서 검색할 단어")
        self.name_edit = QLineEdit(tile.name if tile else "")
        self.name_edit.setPlaceholderText("비우면 검색어를 그대로 사용")

        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)
        colors = QHBoxLayout()
        colors.setSpacing(4)
        self.auto_button = self._color_button("", "자동")
        colors.addWidget(self.auto_button)
        self.color_buttons: dict[str, QToolButton] = {}
        for color in PALETTE:
            button = self._color_button(color, "")
            self.color_buttons[color] = button
            colors.addWidget(button)
        current = tile.color if tile else ""
        (self.color_buttons.get(current) or self.auto_button).setChecked(True)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = self.buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setText("저장")
        self.buttons.button(QDialogButtonBox.Cancel).setText("취소")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("검색어", self.query_edit)
        form.addRow("표시 이름", self.name_edit)
        form.addRow("색상", colors)
        form.addRow(self.buttons)

        self.query_edit.textChanged.connect(self._update_ok)
        self._update_ok()

    def _color_button(self, color: str, text: str) -> QToolButton:
        button = QToolButton(self)
        button.setCheckable(True)
        button.setProperty("color", color)
        button.setText(text)
        button.setFixedSize(QSize(44 if text else 24, 24))
        if color:
            button.setStyleSheet(
                f"QToolButton {{ background: {color}; border: 2px solid transparent; border-radius: 4px; }}"
                "QToolButton:checked { border-color: #202020; }"
            )
        self.color_group.addButton(button)
        return button

    def _update_ok(self) -> None:
        self.ok_button.setEnabled(bool(self.query_edit.text().strip()))

    def selected_color(self) -> str:
        button = self.color_group.checkedButton()
        return str(button.property("color") or "") if button else ""

    def result_tile(self) -> Tile:
        query = self.query_edit.text().strip()
        name = self.name_edit.text().strip()
        color = self.selected_color()
        if self._tile is not None:
            return Tile(query=query, name=name, color=color, id=self._tile.id)
        return Tile(query=query, name=name, color=color)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_tile_dialog.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```powershell
git add src/yt_launcher/ui/tile_dialog.py tests/test_tile_dialog.py
git commit -m "feat: add tile add/edit dialog"
```

---

### Task 12: 런처 창과 트레이

**Files:**
- Create: `src/yt_launcher/ui/launcher_window.py`, `src/yt_launcher/ui/tray.py`
- Test: `tests/test_launcher_window.py`

**Interfaces:**
- Consumes: `ui.tile_grid.TileGrid`, `geometry.Rect`, `version.APP_NAME`, `win32.pin_to_desktop/send_to_bottom`
- Produces:
  - `class LauncherWindow(QWidget)(menu: QMenu)` — signals `tile_clicked(str)`, `add_requested()`, `edit_requested(str)`, `delete_requested(str)`, `order_changed(list)`, `update_clicked()`, `geometry_changed(object)` (Rect); attributes `header: Header` (`header.update_button: QPushButton`), `progress: QProgressBar`, `grid: TileGrid`; methods `set_tiles(tiles)`, `set_locked(locked: bool)`, `show_update_badge(text: str)`, `hide_update_badge()`, `set_progress(done: int, total: int)`, `hide_progress()`, `_edges_at(pos: QPoint) -> Qt.Edge`, `_emit_geometry()`.
  - 상수 `EDGE = 6`, `MIN_W = 240`, `MIN_H = 200`, `GEOMETRY_SAVE_DELAY_MS = 500`
  - `class Tray(QSystemTrayIcon)(icon: QIcon, menu: QMenu)` — signal `show_requested()`; methods `notify(message: str) -> None`, `_on_activated(reason)`.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_launcher_window.py`

```python
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from yt_launcher.geometry import Rect
from yt_launcher.models import Tile
from yt_launcher.resources import app_icon
from yt_launcher.ui.launcher_window import LauncherWindow
from yt_launcher.ui.tray import Tray


def test_window_flags_make_desktop_widget(qapp):
    window = LauncherWindow(QMenu())
    flags = window.windowFlags()
    assert flags & Qt.FramelessWindowHint
    assert flags & Qt.WindowStaysOnBottomHint
    assert (flags & Qt.Tool) == Qt.Tool
    assert window.minimumSize().width() == 240
    assert window.minimumSize().height() == 200


def test_tiles_badge_and_progress(qapp):
    window = LauncherWindow(QMenu())
    window.set_tiles([Tile(query="a"), Tile(query="b")])
    assert window.grid.count() == 3
    assert window.header.update_button.isHidden()
    window.show_update_badge("업데이트 있음 v0.2.0")
    assert not window.header.update_button.isHidden()
    assert window.header.update_button.text() == "업데이트 있음 v0.2.0"
    window.hide_update_badge()
    assert window.header.update_button.isHidden()
    assert window.progress.isHidden()
    window.set_progress(5, 10)
    assert not window.progress.isHidden()
    assert window.progress.value() == 5
    window.hide_progress()
    assert window.progress.isHidden()


def test_update_badge_click_emits(qapp):
    window = LauncherWindow(QMenu())
    clicked = []
    window.update_clicked.connect(lambda: clicked.append(True))
    window.show_update_badge("업데이트 있음 v0.2.0")
    window.header.update_button.click()
    assert clicked == [True]


def test_edges_at(qapp):
    window = LauncherWindow(QMenu())
    window.resize(300, 300)
    assert window._edges_at(QPoint(1, 1)) == Qt.Edge.LeftEdge | Qt.Edge.TopEdge
    assert window._edges_at(QPoint(299, 150)) == Qt.Edge.RightEdge
    assert window._edges_at(QPoint(150, 299)) == Qt.Edge.BottomEdge
    assert window._edges_at(QPoint(150, 150)) == Qt.Edge(0)


def test_geometry_signal_reports_rect(qapp):
    window = LauncherWindow(QMenu())
    got = []
    window.geometry_changed.connect(got.append)
    window.setGeometry(10, 20, 300, 400)
    window._emit_geometry()
    assert got[-1] == Rect(10, 20, 300, 400)


def test_tray_click_requests_show(qapp):
    tray = Tray(app_icon(), QMenu())
    shown = []
    tray.show_requested.connect(lambda: shown.append(True))
    tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
    tray._on_activated(QSystemTrayIcon.ActivationReason.Context)
    assert shown == [True]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_launcher_window.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.ui.launcher_window'`

- [ ] **Step 3: 런처 창 구현** — `src/yt_launcher/ui/launcher_window.py`

```python
"""바탕화면 위젯 형태의 런처 창."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import win32
from ..geometry import Rect
from ..version import APP_NAME
from .tile_grid import TileGrid

EDGE = 6
MIN_W = 240
MIN_H = 200
GEOMETRY_SAVE_DELAY_MS = 500

STYLE = """
#launcher { background: #16181D; border: 1px solid #2A2E37; }
#header { background: #1F232B; }
#title { color: #F1F3F5; font-weight: bold; font-size: 13px; }
#updateBadge { background: #E53935; color: #FFFFFF; border: none; border-radius: 9px;
               padding: 2px 10px; font-weight: bold; }
#menuButton { color: #C9CED6; background: transparent; border: none; font-size: 16px; padding: 0 6px; }
#menuButton::menu-indicator { image: none; }
#progress { background: #2A2E37; border: none; }
#progress::chunk { background: #E53935; }
#tileGrid { background: transparent; border: none; }
"""

_CURSORS = {
    Qt.Edge.LeftEdge | Qt.Edge.TopEdge: Qt.SizeFDiagCursor,
    Qt.Edge.RightEdge | Qt.Edge.BottomEdge: Qt.SizeFDiagCursor,
    Qt.Edge.RightEdge | Qt.Edge.TopEdge: Qt.SizeBDiagCursor,
    Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: Qt.SizeBDiagCursor,
    Qt.Edge.LeftEdge: Qt.SizeHorCursor,
    Qt.Edge.RightEdge: Qt.SizeHorCursor,
    Qt.Edge.TopEdge: Qt.SizeVerCursor,
    Qt.Edge.BottomEdge: Qt.SizeVerCursor,
}


class Header(QWidget):
    """제목·업데이트 배지·메뉴. 드래그하면 창을 옮긴다."""

    def __init__(self, menu: QMenu, can_move: Callable[[], bool], parent=None):
        super().__init__(parent)
        self._can_move = can_move
        self.setObjectName("header")
        self.setAttribute(Qt.WA_StyledBackground, True)

        title = QLabel(APP_NAME)
        title.setObjectName("title")
        self.update_button = QPushButton()
        self.update_button.setObjectName("updateBadge")
        self.update_button.setCursor(Qt.PointingHandCursor)
        self.update_button.hide()
        menu_button = QToolButton()
        menu_button.setObjectName("menuButton")
        menu_button.setText("⋯")
        menu_button.setMenu(menu)
        menu_button.setPopupMode(QToolButton.InstantPopup)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(self.update_button)
        layout.addWidget(menu_button)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._can_move() and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
            return
        super().mousePressEvent(event)


class LauncherWindow(QWidget):
    tile_clicked = Signal(str)
    add_requested = Signal()
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    order_changed = Signal(list)
    update_clicked = Signal()
    geometry_changed = Signal(object)

    def __init__(self, menu: QMenu):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnBottomHint)
        self.setObjectName("launcher")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(MIN_W, MIN_H)
        self.setMouseTracking(True)
        self.setStyleSheet(STYLE)
        self._locked = False
        self._pinned = False

        self.header = Header(menu, lambda: not self._locked, self)
        self.progress = QProgressBar(self)
        self.progress.setObjectName("progress")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        self.grid = TileGrid(self)
        self.grid.setObjectName("tileGrid")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(EDGE, EDGE, EDGE, EDGE)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.progress)
        layout.addWidget(self.grid, 1)

        self.header.update_button.clicked.connect(lambda: self.update_clicked.emit())
        self.grid.tile_clicked.connect(self.tile_clicked)
        self.grid.add_requested.connect(self.add_requested)
        self.grid.edit_requested.connect(self.edit_requested)
        self.grid.delete_requested.connect(self.delete_requested)
        self.grid.order_changed.connect(self.order_changed)

        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.setInterval(GEOMETRY_SAVE_DELAY_MS)
        self._geometry_timer.timeout.connect(self._emit_geometry)

    # 상태 표시
    def set_tiles(self, tiles) -> None:
        self.grid.set_tiles(tiles)

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        if locked:
            self.unsetCursor()

    def show_update_badge(self, text: str) -> None:
        self.header.update_button.setText(text)
        self.header.update_button.show()

    def hide_update_badge(self) -> None:
        self.header.update_button.hide()

    def set_progress(self, done: int, total: int) -> None:
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(min(done, max(total, 1)))
        self.progress.show()

    def hide_progress(self) -> None:
        self.progress.hide()

    # 바탕화면 레이어
    def showEvent(self, event) -> None:
        super().showEvent(event)
        hwnd = int(self.winId())
        if not self._pinned:
            self._pinned = win32.pin_to_desktop(hwnd)
        win32.send_to_bottom(hwnd)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            QTimer.singleShot(0, self._sink_if_app_inactive)

    def _sink_if_app_inactive(self) -> None:
        # 앱의 대화상자·메뉴로 포커스가 옮겨간 경우에는 내리지 않는다.
        if QApplication.activeWindow() is None and self.isVisible():
            win32.send_to_bottom(int(self.winId()))

    # 위치·크기
    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._geometry_timer.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._geometry_timer.start()

    def _emit_geometry(self) -> None:
        g = self.geometry()
        self.geometry_changed.emit(Rect(g.x(), g.y(), g.width(), g.height()))

    def _edges_at(self, pos: QPoint) -> Qt.Edge:
        edges = Qt.Edge(0)
        if pos.x() <= EDGE:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - EDGE:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= EDGE:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= self.height() - EDGE:
            edges |= Qt.Edge.BottomEdge
        return edges

    def mouseMoveEvent(self, event) -> None:
        cursor = None if self._locked else _CURSORS.get(self._edges_at(event.position().toPoint()))
        if cursor is None:
            self.unsetCursor()
        else:
            self.setCursor(cursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and not self._locked and self.windowHandle():
            edges = self._edges_at(event.position().toPoint())
            if edges:
                self.windowHandle().startSystemResize(edges)
                return
        super().mousePressEvent(event)
```

- [ ] **Step 4: 트레이 구현** — `src/yt_launcher/ui/tray.py`

```python
"""트레이 아이콘."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..version import APP_NAME

NOTIFY_MS = 5000


class Tray(QSystemTrayIcon):
    show_requested = Signal()

    def __init__(self, icon: QIcon, menu: QMenu, parent=None):
        super().__init__(icon, parent)
        self.setToolTip(APP_NAME)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_requested.emit()

    def notify(self, message: str) -> None:
        self.showMessage(APP_NAME, message, self.icon(), NOTIFY_MS)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_launcher_window.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```powershell
git add src/yt_launcher/ui/launcher_window.py src/yt_launcher/ui/tray.py tests/test_launcher_window.py
git commit -m "feat: add desktop-layer launcher window and tray icon"
```

---

### Task 13: 애플리케이션 컨트롤러

**Files:**
- Create: `src/yt_launcher/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `Storage.load/save`, `Config`, `Tile`, `default_rect`, `is_visible_on_any`, `Rect`, `chrome.open_search/find_chrome`, `updater.fetch_latest/is_newer/download_and_verify/launch_installer/Release/UpdateError`, `AutoStart`, `launch_command`, `LauncherWindow`, `TileDialog`, `Tray`, `app_icon`, `REPO`, `__version__`
- Produces: `class LauncherApp(QObject)(qapp, storage: Storage, *, autostart: AutoStart | None = None, frozen: bool | None = None, show: bool = True)` with attributes `config`, `window`, `tray`, `menu`, `release`; public methods `add_tile(tile)`, `update_tile(tile)`, `remove_tile(tile_id)`, `reorder(ids: list[str])`, `open_tile(tile_id)`, `set_locked(locked)`, `set_autostart(enabled)`, `reset_geometry()`, `check_updates(manual: bool = False)`, `start_update()`, `show_launcher()`, `open_releases_page()`, `quit()`; 내부 `_on_update_found(release)`.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_app.py`

```python
from yt_launcher.app import LauncherApp
from yt_launcher.autostart import AutoStart
from yt_launcher.geometry import Rect
from yt_launcher.models import Tile
from yt_launcher.storage import Config, Storage
from yt_launcher.updater import Release
from yt_launcher.version import __version__


class FakeBackend:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def delete(self):
        self.value = None


def make_app(qapp, storage, backend=None, frozen=False):
    return LauncherApp(
        qapp, storage, autostart=AutoStart(backend or FakeBackend()), frozen=frozen, show=False
    )


def test_tile_crud_and_reorder_persist(qapp, tmp_path):
    storage = Storage(tmp_path)
    app = make_app(qapp, storage)
    a, b = Tile(query="a"), Tile(query="b")
    app.add_tile(a)
    app.add_tile(b)
    assert app.window.grid.tile_ids() == [a.id, b.id]
    app.reorder([b.id, a.id])
    app.update_tile(Tile(query="a2", id=a.id))
    app.remove_tile(b.id)
    saved, _ = storage.load()
    assert [(t.id, t.query) for t in saved.tiles] == [(a.id, "a2")]
    assert app.window.grid.tile_ids() == [a.id]


def test_reorder_keeps_unknown_tiles(qapp, tmp_path):
    app = make_app(qapp, Storage(tmp_path))
    a, b, c = Tile(query="a"), Tile(query="b"), Tile(query="c")
    for tile in (a, b, c):
        app.add_tile(tile)
    app.reorder([c.id, a.id])
    assert [t.id for t in app.config.tiles] == [c.id, a.id, b.id]


def test_records_last_run_version(qapp, tmp_path):
    storage = Storage(tmp_path)
    make_app(qapp, storage)
    assert storage.load()[0].last_run_version == __version__


def test_restores_saved_geometry_or_defaults(qapp, tmp_path):
    storage = Storage(tmp_path)
    storage.save(Config(window=Rect(-9000, -9000, 300, 300)))
    app = make_app(qapp, storage)
    g = app.window.geometry()
    assert g.x() > -9000  # 화면 밖 위치는 기본 위치로 복구


def test_update_found_shows_badge_once(qapp, tmp_path):
    storage = Storage(tmp_path)
    app = make_app(qapp, storage)
    release = Release("v99.0.0", "99.0.0", "https://example/release", None, None)
    app._on_update_found(release)
    assert not app.window.header.update_button.isHidden()
    assert "99.0.0" in app.window.header.update_button.text()
    assert storage.load()[0].notified_version == "99.0.0"
    assert app.release is release


def test_frozen_applies_saved_autostart_preference(qapp, tmp_path):
    storage = Storage(tmp_path)
    storage.save(Config(autostart=False))
    backend = FakeBackend('"C:\\old\\YTLauncher.exe"')
    make_app(qapp, storage, backend=backend, frozen=True)
    assert backend.value is None


def test_dev_mode_does_not_touch_autostart(qapp, tmp_path):
    storage = Storage(tmp_path)
    storage.save(Config(autostart=False))
    backend = FakeBackend('"C:\\old\\YTLauncher.exe"')
    make_app(qapp, storage, backend=backend, frozen=False)
    assert backend.value == '"C:\\old\\YTLauncher.exe"'


def test_set_autostart_updates_config_and_registry(qapp, tmp_path):
    storage = Storage(tmp_path)
    backend = FakeBackend()
    app = make_app(qapp, storage, backend=backend)
    app.set_autostart(True)
    assert backend.value is not None
    assert storage.load()[0].autostart is True
    app.set_autostart(False)
    assert backend.value is None
    assert storage.load()[0].autostart is False


def test_set_locked_persists(qapp, tmp_path):
    storage = Storage(tmp_path)
    app = make_app(qapp, storage)
    app.set_locked(True)
    assert storage.load()[0].locked is True
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.app'`

- [ ] **Step 3: 구현** — `src/yt_launcher/app.py`

```python
"""애플리케이션 컨트롤러: 설정·창·트레이·크롬 실행·업데이트를 연결한다."""

from __future__ import annotations

import logging
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, QRect, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QMenu, QMessageBox

from . import chrome, updater
from .autostart import AutoStart, launch_command
from .geometry import Rect, default_rect, is_visible_on_any
from .models import Tile
from .resources import app_icon
from .storage import Storage
from .ui.launcher_window import LauncherWindow
from .ui.tile_dialog import TileDialog
from .ui.tray import Tray
from .version import REPO, __version__

log = logging.getLogger(__name__)

FIRST_CHECK_DELAY_MS = 30_000
CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000
CLICK_DEBOUNCE_S = 1.0
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"
UPDATE_DIR_NAME = "YT-Launcher-update"


def _to_rect(rect: QRect) -> Rect:
    return Rect(rect.x(), rect.y(), rect.width(), rect.height())


class _Signals(QObject):
    """백그라운드 스레드 → UI 스레드 전달용."""

    update_found = Signal(object)
    update_none = Signal(bool, bool)  # manual, ok
    download_progress = Signal(int, int)
    download_done = Signal(object)
    download_failed = Signal(str)
    chrome_done = Signal(bool)


class LauncherApp(QObject):
    def __init__(
        self,
        qapp,
        storage: Storage,
        *,
        autostart: AutoStart | None = None,
        frozen: bool | None = None,
        show: bool = True,
    ):
        super().__init__()
        self.qapp = qapp
        self.storage = storage
        self.autostart = autostart or AutoStart()
        self.frozen = getattr(sys, "frozen", False) if frozen is None else frozen
        self.config, recovered = storage.load()
        self.release: updater.Release | None = None
        self._downloading = False
        self._last_click: dict[str, float] = {}
        self.signals = _Signals()

        self.menu = QMenu()
        self._build_menu()
        self.window = LauncherWindow(self.menu)
        self.tray = Tray(app_icon(), self.menu)
        self._connect()

        self._restore_geometry()
        self.window.set_locked(self.config.locked)
        self.window.set_tiles(self.config.tiles)
        self._apply_autostart_preference()

        self._update_timer = QTimer(self)
        self._update_timer.setInterval(CHECK_INTERVAL_MS)
        self._update_timer.timeout.connect(lambda: self.check_updates(manual=False))

        if show:
            self.window.show()
            self.tray.show()
            QTimer.singleShot(FIRST_CHECK_DELAY_MS, lambda: self.check_updates(manual=False))
            self._update_timer.start()

        self._announce_updated()
        if recovered:
            self.tray.notify("설정 파일이 손상되어 초기화했습니다. 이전 파일은 config.json.bak에 있습니다.")

    # 구성
    def _build_menu(self) -> None:
        self.action_show = self.menu.addAction("런처 보이기")
        self.action_reset = self.menu.addAction("위치·크기 초기화")
        self.action_lock = self.menu.addAction("위치 잠금")
        self.action_lock.setCheckable(True)
        self.action_lock.setChecked(self.config.locked)
        self.action_autostart = self.menu.addAction("윈도우 시작 시 실행")
        self.action_autostart.setCheckable(True)
        self.menu.addSeparator()
        self.action_check = self.menu.addAction("업데이트 확인")
        self.action_releases = self.menu.addAction("릴리스 페이지 열기")
        self.menu.addSeparator()
        self.action_quit = self.menu.addAction("종료")
        self.menu.aboutToShow.connect(
            lambda: self.action_autostart.setChecked(self.autostart.is_enabled())
        )

    def _connect(self) -> None:
        self.action_show.triggered.connect(self.show_launcher)
        self.action_reset.triggered.connect(self.reset_geometry)
        self.action_lock.toggled.connect(self.set_locked)
        self.action_autostart.triggered.connect(self.set_autostart)
        self.action_check.triggered.connect(lambda: self.check_updates(manual=True))
        self.action_releases.triggered.connect(self.open_releases_page)
        self.action_quit.triggered.connect(self.quit)
        self.tray.show_requested.connect(self.show_launcher)

        w = self.window
        w.tile_clicked.connect(self.open_tile)
        w.add_requested.connect(self._add_with_dialog)
        w.edit_requested.connect(self._edit_with_dialog)
        w.delete_requested.connect(self._confirm_delete)
        w.order_changed.connect(self.reorder)
        w.update_clicked.connect(self.start_update)
        w.geometry_changed.connect(self._save_geometry)

        s = self.signals
        s.update_found.connect(self._on_update_found)
        s.update_none.connect(self._on_update_none)
        s.download_progress.connect(w.set_progress)
        s.download_done.connect(self._on_download_done)
        s.download_failed.connect(self._on_download_failed)
        s.chrome_done.connect(self._on_chrome_done)

    def _save(self) -> None:
        try:
            self.storage.save(self.config)
        except OSError:
            log.exception("설정 저장 실패")

    # 창 위치
    def _primary_work_area(self) -> Rect:
        return _to_rect(QGuiApplication.primaryScreen().availableGeometry())

    def _restore_geometry(self) -> None:
        works = [_to_rect(screen.availableGeometry()) for screen in QGuiApplication.screens()]
        rect = self.config.window
        if rect is None or not is_visible_on_any(rect, works):
            rect = default_rect(self._primary_work_area())
        self.window.setGeometry(rect.x, rect.y, rect.w, rect.h)

    def reset_geometry(self) -> None:
        rect = default_rect(self._primary_work_area())
        self.window.setGeometry(rect.x, rect.y, rect.w, rect.h)
        self._save_geometry(rect)

    def _save_geometry(self, rect: Rect) -> None:
        self.config.window = rect
        self._save()

    def set_locked(self, locked: bool) -> None:
        self.config.locked = locked
        self.window.set_locked(locked)
        self._save()

    def show_launcher(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    # 타일
    def _find(self, tile_id: str) -> Tile | None:
        return next((t for t in self.config.tiles if t.id == tile_id), None)

    def _tiles_changed(self) -> None:
        self.window.set_tiles(self.config.tiles)
        self._save()

    def add_tile(self, tile: Tile) -> None:
        self.config.tiles.append(tile)
        self._tiles_changed()

    def update_tile(self, tile: Tile) -> None:
        self.config.tiles = [tile if t.id == tile.id else t for t in self.config.tiles]
        self._tiles_changed()

    def remove_tile(self, tile_id: str) -> None:
        self.config.tiles = [t for t in self.config.tiles if t.id != tile_id]
        self._tiles_changed()

    def reorder(self, ids: list[str]) -> None:
        # 그리드는 이미 새 순서로 그려져 있으므로 설정만 갱신한다 (dropEvent 도중 호출됨).
        by_id = {t.id: t for t in self.config.tiles}
        ordered = [by_id.pop(tile_id) for tile_id in ids if tile_id in by_id]
        self.config.tiles = ordered + list(by_id.values())
        self._save()

    def _add_with_dialog(self) -> None:
        dialog = TileDialog(self.window)
        if dialog.exec() == QDialog.Accepted:
            self.add_tile(dialog.result_tile())

    def _edit_with_dialog(self, tile_id: str) -> None:
        tile = self._find(tile_id)
        if tile is None:
            return
        dialog = TileDialog(self.window, tile)
        if dialog.exec() == QDialog.Accepted:
            self.update_tile(dialog.result_tile())

    def _confirm_delete(self, tile_id: str) -> None:
        tile = self._find(tile_id)
        if tile is None:
            return
        answer = QMessageBox.question(self.window, "타일 삭제", f"'{tile.label}' 타일을 삭제할까요?")
        if answer == QMessageBox.StandardButton.Yes:
            self.remove_tile(tile_id)

    def open_tile(self, tile_id: str) -> None:
        tile = self._find(tile_id)
        if tile is None:
            return
        now = time.monotonic()
        if now - self._last_click.get(tile_id, -CLICK_DEBOUNCE_S) < CLICK_DEBOUNCE_S:
            return
        self._last_click[tile_id] = now
        threading.Thread(target=self._open_in_background, args=(tile.query,), daemon=True).start()

    def _open_in_background(self, query: str) -> None:
        try:
            used_chrome = chrome.open_search(query, chrome.find_chrome())
        except Exception:
            log.exception("검색 열기 실패")
            return
        self.signals.chrome_done.emit(used_chrome)

    def _on_chrome_done(self, used_chrome: bool) -> None:
        if used_chrome or self.config.chrome_notice_shown:
            return
        self.config.chrome_notice_shown = True
        self._save()
        self.tray.notify("크롬을 찾지 못해 기본 브라우저로 열었습니다.")

    # 자동 실행
    def set_autostart(self, enabled: bool) -> None:
        self.config.autostart = enabled
        self._save()
        self._sync_autostart(enabled)

    def _sync_autostart(self, enabled: bool) -> None:
        try:
            if enabled:
                self.autostart.enable(launch_command())
            else:
                self.autostart.disable()
        except OSError:
            log.exception("자동 실행 설정 실패")

    def _apply_autostart_preference(self) -> None:
        # 업데이트 설치가 Run 키를 되살려도 사용자가 앱에서 고른 값을 유지한다.
        if self.frozen and self.config.autostart is not None:
            self._sync_autostart(self.config.autostart)

    # 업데이트
    def _announce_updated(self) -> None:
        previous = self.config.last_run_version
        if previous == __version__:
            return
        if previous and updater.is_newer(__version__, previous):
            self.tray.notify(f"v{__version__} 버전으로 업데이트되었습니다.")
        self.config.last_run_version = __version__
        self._save()

    def check_updates(self, manual: bool = False) -> None:
        threading.Thread(target=self._check_in_background, args=(manual,), daemon=True).start()

    def _check_in_background(self, manual: bool) -> None:
        try:
            release = updater.fetch_latest(REPO)
        except Exception:
            log.warning("업데이트 확인 실패", exc_info=True)
            self.signals.update_none.emit(manual, False)
            return
        if release and updater.is_newer(release.version, __version__):
            self.signals.update_found.emit(release)
        else:
            self.signals.update_none.emit(manual, True)

    def _on_update_found(self, release: updater.Release) -> None:
        self.release = release
        if not self._downloading:
            self.window.show_update_badge(f"업데이트 있음 v{release.version}")
        if self.config.notified_version != release.version:
            self.config.notified_version = release.version
            self._save()
            self.tray.notify(f"새 버전(v{release.version})이 나왔습니다. 런처의 업데이트 버튼을 눌러 설치하세요.")

    def _on_update_none(self, manual: bool, ok: bool) -> None:
        if manual:
            self.tray.notify("최신 버전입니다." if ok else "업데이트를 확인하지 못했습니다. 인터넷 연결을 확인하세요.")

    def start_update(self) -> None:
        if self.release is None or self._downloading:
            return
        answer = QMessageBox.question(
            self.window,
            "업데이트",
            f"v{self.release.version} 버전으로 업데이트할까요?\n런처가 잠시 꺼졌다 켜집니다.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._downloading = True
        self.window.hide_update_badge()
        self.window.set_progress(0, 1)
        threading.Thread(target=self._download_in_background, args=(self.release,), daemon=True).start()

    def _download_in_background(self, release: updater.Release) -> None:
        dest = Path(tempfile.gettempdir()) / UPDATE_DIR_NAME
        try:
            path = updater.download_and_verify(release, dest, progress=self.signals.download_progress.emit)
        except Exception as exc:
            log.warning("업데이트 다운로드 실패: %s", exc)
            self.signals.download_failed.emit(str(exc))
            return
        self.signals.download_done.emit(path)

    def _on_download_done(self, path: Path) -> None:
        try:
            updater.launch_installer(path)
        except OSError as exc:
            self._on_download_failed(str(exc))
            return
        self.quit()

    def _on_download_failed(self, message: str) -> None:
        self._downloading = False
        self.window.hide_progress()
        self.window.show_update_badge("업데이트 실패 · 다시 시도")
        self.tray.notify(f"업데이트에 실패했습니다: {message}")

    def open_releases_page(self) -> None:
        url = self.release.html_url if self.release and self.release.html_url else RELEASES_URL
        webbrowser.open(url)

    def quit(self) -> None:
        self.tray.hide()
        self.qapp.quit()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_app.py -v`
Expected: 9 passed

- [ ] **Step 5: 전체 테스트**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 모든 테스트 통과 (실패 0)

- [ ] **Step 6: Commit**

```powershell
git add src/yt_launcher/app.py tests/test_app.py
git commit -m "feat: add LauncherApp controller wiring tiles, chrome and updates"
```

---

### Task 14: 진입점과 단일 인스턴스

**Files:**
- Create: `src/yt_launcher/single_instance.py`, `src/yt_launcher/main.py`, `src/yt_launcher/__main__.py`, `launcher.py`
- Test: `tests/test_single_instance.py`

**Interfaces:**
- Consumes: `LauncherApp`, `Storage`, `default_dir`, `win32.create_mutex`, `version.APP_NAME/MUTEX_NAME`
- Produces: `class SingleInstance(QObject)(name: str)` with signal `activated()`, method `acquire() -> bool` (첫 인스턴스면 True, 이미 실행 중이면 기존 인스턴스에 "show"를 보내고 False); `main.setup_logging(log_dir: Path) -> None`; `main.main() -> int`.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_single_instance.py`

```python
import uuid

from yt_launcher.single_instance import SingleInstance


def test_second_instance_signals_first(qapp):
    name = f"YTLauncherTest-{uuid.uuid4().hex}"
    first = SingleInstance(name)
    assert first.acquire() is True
    activated = []
    first.activated.connect(lambda: activated.append(True))

    second = SingleInstance(name)
    assert second.acquire() is False

    for _ in range(50):
        qapp.processEvents()
        if activated:
            break
    assert activated == [True]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv\Scripts\python -m pytest tests/test_single_instance.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_launcher.single_instance'`

- [ ] **Step 3: 단일 인스턴스 구현** — `src/yt_launcher/single_instance.py`

```python
"""QLocalServer로 앱 중복 실행을 막는다."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

CONNECT_TIMEOUT_MS = 300


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.server: QLocalServer | None = None

    def acquire(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if socket.waitForConnected(CONNECT_TIMEOUT_MS):
            socket.write(b"show")
            socket.flush()
            socket.waitForBytesWritten(CONNECT_TIMEOUT_MS)
            socket.disconnectFromServer()
            return False
        QLocalServer.removeServer(self.name)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_new_connection)
        self.server.listen(self.name)
        return True

    def _on_new_connection(self) -> None:
        while self.server.hasPendingConnections():
            connection = self.server.nextPendingConnection()
            connection.disconnected.connect(connection.deleteLater)
            connection.disconnectFromServer()
            self.activated.emit()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv\Scripts\python -m pytest tests/test_single_instance.py -v`
Expected: 1 passed

- [ ] **Step 5: 진입점 작성**

`src/yt_launcher/main.py`:

```python
"""앱 진입점."""

from __future__ import annotations

import getpass
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtWidgets import QApplication

from . import win32
from .app import LauncherApp
from .single_instance import SingleInstance
from .storage import Storage, default_dir
from .version import APP_NAME, MUTEX_NAME, __version__

LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 3


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "launcher.log", maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    sys.excepthook = lambda *exc: logging.getLogger("yt_launcher").critical(
        "처리되지 않은 예외", exc_info=exc
    )


def main() -> int:
    data_dir = default_dir()
    setup_logging(data_dir / "logs")
    logging.getLogger(__name__).info("YT Launcher %s 시작", __version__)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    instance = SingleInstance(f"YTLauncher-{getpass.getuser()}")
    if not instance.acquire():
        return 0
    mutex = win32.create_mutex(MUTEX_NAME)  # 설치 프로그램이 실행 중 여부를 감지하는 데 쓴다

    launcher = LauncherApp(app, Storage(data_dir))
    instance.activated.connect(launcher.show_launcher)
    code = app.exec()
    del mutex
    return code
```

`src/yt_launcher/__main__.py`:

```python
import sys

from .main import main

sys.exit(main())
```

`launcher.py` (저장소 루트, PyInstaller 진입 스크립트):

```python
import sys

from yt_launcher.main import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: 앱 실행 확인 (수동)**

Run: `.venv\Scripts\python -m yt_launcher`
Expected:
- 주 모니터 우상단에 360×480 런처가 뜨고, 작업표시줄에는 아이콘이 없고 트레이에 빨간 재생 아이콘이 보인다.
- `＋`로 "로파이 음악" 타일을 추가하면 타일이 생기고, 누르면 크롬이 최대화 창으로 검색 결과를 연다.
- 다른 창을 열면 런처가 그 뒤로 깔린다. 헤더 드래그로 이동, 가장자리로 크기 조절이 된다.
- 같은 명령을 다른 터미널에서 한 번 더 실행하면 새 창이 생기지 않고 즉시 종료된다.
- 트레이 메뉴 "종료"로 끄고 다시 실행하면 타일과 위치가 복원된다.
- `%APPDATA%\YT-Launcher\config.json`과 `logs\launcher.log`가 생성된다.

- [ ] **Step 7: 전체 테스트 후 Commit**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 실패 0

```powershell
git add src/yt_launcher/single_instance.py src/yt_launcher/main.py src/yt_launcher/__main__.py launcher.py tests/test_single_instance.py
git commit -m "feat: add entry point with single-instance guard and logging"
```

---

### Task 15: 빌드 스크립트와 설치 프로그램

**Files:**
- Create: `scripts/build.ps1`, `installer/setup.iss`

**Interfaces:**
- Consumes: `launcher.py`, `src/yt_launcher/assets/icon.ico`, `version.__version__`, `MUTEX_NAME = "YTLauncherMutex"`, Run 값 `YTLauncher`
- Produces: `dist\YTLauncher\YTLauncher.exe` (PyInstaller onedir), `dist\installer\YT-Launcher-Setup-<버전>.exe`, `dist\installer\SHA256SUMS.txt`. `scripts/build.ps1 [-Version <x.y.z>] [-Python <path>]`.

- [ ] **Step 1: Inno Setup 설치 (로컬, 1회)**

Run: `winget install -e --id JRSoftware.InnoSetup`
Expected: 설치 완료. 아래 중 하나에 `ISCC.exe`가 있다: `${env:ProgramFiles(x86)}\Inno Setup 6`, `$env:ProgramFiles\Inno Setup 6`, `$env:LOCALAPPDATA\Programs\Inno Setup 6`.

한국어 메시지 파일 확인:
Run: `Get-ChildItem "${env:ProgramFiles(x86)}\Inno Setup 6\Languages\Korean.isl", "$env:LOCALAPPDATA\Programs\Inno Setup 6\Languages\Korean.isl" -ErrorAction SilentlyContinue`
Expected: `Korean.isl` 한 개가 보인다. 없으면 Step 3의 `[Languages]` 줄을 `Name: "korean"; MessagesFile: "compiler:Default.isl"`로 바꾼다 (화면 기본 문구만 영어가 되고 커스텀 문구는 한국어 유지).

- [ ] **Step 2: 빌드 스크립트 작성** — `scripts/build.ps1`

```powershell
<#
.SYNOPSIS
  PyInstaller로 앱을 묶고 Inno Setup으로 설치 프로그램과 SHA256SUMS.txt를 만든다.
.EXAMPLE
  ./scripts/build.ps1
  ./scripts/build.ps1 -Version 0.2.0 -Python python
#>
param(
    [string]$Version,
    [string]$Python
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not $Python) {
    $venv = Join-Path $root ".venv\Scripts\python.exe"
    $Python = if (Test-Path $venv) { $venv } else { "python" }
}
if (-not $Version) {
    $Version = (& $Python -c "from yt_launcher.version import __version__; print(__version__)").Trim()
}
Write-Host "Building YT Launcher $Version"

& $Python -m PyInstaller --noconfirm --clean --windowed `
    --name YTLauncher `
    --icon "src\yt_launcher\assets\icon.ico" `
    --add-data "src\yt_launcher\assets;yt_launcher\assets" `
    --paths src `
    --distpath dist --workpath build `
    launcher.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$iscc = $null
$command = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($command) { $iscc = $command.Source }
if (-not $iscc) {
    $iscc = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) { throw "ISCC.exe를 찾을 수 없습니다. Inno Setup 6을 설치하세요." }

& $iscc "/DAppVersion=$Version" "installer\setup.iss"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }

$setupName = "YT-Launcher-Setup-$Version.exe"
$setupPath = Join-Path $root "dist\installer\$setupName"
$hash = (Get-FileHash $setupPath -Algorithm SHA256).Hash.ToLower()
"$hash  $setupName" | Set-Content (Join-Path $root "dist\installer\SHA256SUMS.txt") -Encoding ascii
Write-Host "Done: $setupPath"
```

- [ ] **Step 3: Inno Setup 스크립트 작성** — `installer/setup.iss`

```iss
; YT Launcher 설치 스크립트. scripts/build.ps1이 /DAppVersion=<버전>을 넘긴다.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "YT Launcher"
#define AppExe "YTLauncher.exe"

[Setup]
AppId={{8F3C2A71-5B4E-4C9D-9A16-3E7D2B0C5F48}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=ssenu
AppPublisherURL=https://github.com/ssenu/YT-launcher
AppUpdatesURL=https://github.com/ssenu/YT-launcher/releases
DefaultDirName={localappdata}\Programs\YT-Launcher
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=YT-Launcher-Setup-{#AppVersion}
SetupIconFile=..\src\yt_launcher\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "autostart"; Description: "윈도우 시작 시 자동 실행"; GroupDescription: "추가 옵션:"
Name: "desktopicon"; Description: "바탕화면 바로가기 만들기"; GroupDescription: "추가 옵션:"; Flags: unchecked

[InstallDelete]
; 업그레이드 시 이전 버전의 라이브러리를 지워 섞이지 않게 한다.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\YTLauncher\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "YTLauncher"; ValueData: """{app}\{#AppExe}"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
; 일반 설치: 마지막 화면의 "실행" 체크박스
Filename: "{app}\{#AppExe}"; Description: "YT Launcher 실행"; Flags: nowait postinstall skipifsilent
; 조용한 설치(앱 내 자동 업데이트): 끝나면 바로 다시 실행
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: WizardSilent

[Code]
const
  AppMutexName = 'YTLauncherMutex';
  RunKey = 'Software\Microsoft\Windows\CurrentVersion\Run';

procedure CloseRunningApp(WaitFirst: Boolean);
var
  I, ResultCode: Integer;
begin
  if WaitFirst then
  begin
    { 자동 업데이트 시 앱이 스스로 종료할 시간을 준다 (최대 10초). }
    for I := 1 to 50 do
    begin
      if not CheckForMutexes(AppMutexName) then
        Exit;
      Sleep(200);
    end;
  end;
  if CheckForMutexes(AppMutexName) then
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  CloseRunningApp(WizardSilent);
  Result := '';
end;

function InitializeUninstall(): Boolean;
begin
  CloseRunningApp(False);
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  { 앱 메뉴에서 켠 자동 실행도 함께 지운다. 설정(%APPDATA%\YT-Launcher)은 남긴다. }
  if CurUninstallStep = usPostUninstall then
    RegDeleteValue(HKEY_CURRENT_USER, RunKey, 'YTLauncher');
end;
```

- [ ] **Step 4: 빌드 실행**

Run: `./scripts/build.ps1`
Expected: 마지막 줄 `Done: ...\dist\installer\YT-Launcher-Setup-0.1.0.exe`. `dist\YTLauncher\YTLauncher.exe`, `dist\installer\SHA256SUMS.txt` 존재. `Get-Content dist\installer\SHA256SUMS.txt` → `<64자 소문자 해시>  YT-Launcher-Setup-0.1.0.exe`.

- [ ] **Step 5: 빌드된 exe 단독 실행 확인**

Run: `Start-Process dist\YTLauncher\YTLauncher.exe`
Expected: 콘솔 창 없이 런처가 뜬다 (Task 14 Step 6과 동일 동작). 확인 후 트레이 메뉴 "종료".

- [ ] **Step 6: 조용한 설치·등록·제거 확인**

Run:
```powershell
Start-Process dist\installer\YT-Launcher-Setup-0.1.0.exe -ArgumentList "/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART" -Wait
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F3C2A71-5B4E-4C9D-9A16-3E7D2B0C5F48}_is1" | Select-Object DisplayName, DisplayVersion, InstallLocation
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name YTLauncher
Get-Process YTLauncher
```
Expected: `DisplayName = YT Launcher`, `DisplayVersion = 0.1.0`, `InstallLocation`이 `...\AppData\Local\Programs\YT-Launcher\`; Run 값이 `"...\YTLauncher.exe"`; `YTLauncher` 프로세스 실행 중 (조용한 설치 후 자동 재실행). "설정 → 앱 → 설치된 앱"에 YT Launcher가 보인다.

Run (제거):
```powershell
Start-Process "$env:LOCALAPPDATA\Programs\YT-Launcher\unins000.exe" -ArgumentList "/VERYSILENT","/SUPPRESSMSGBOXES" -Wait
Test-Path "$env:LOCALAPPDATA\Programs\YT-Launcher\YTLauncher.exe"
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name YTLauncher -ErrorAction SilentlyContinue
Test-Path "$env:APPDATA\YT-Launcher\config.json"
```
Expected: `False`, Run 값 없음(출력 없음), 설정 파일은 `True`(유지).

- [ ] **Step 7: Commit**

```powershell
git add scripts/build.ps1 installer/setup.iss
git commit -m "build: add PyInstaller + Inno Setup build script"
```

---

### Task 16: CI·릴리스 자동화와 문서

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `docs/manual-test-checklist.md`, `README.md`

**Interfaces:**
- Consumes: `scripts/build.ps1 -Version <x.y.z> -Python python`, `src/yt_launcher/version.py`의 `__version__ = "..."` 줄
- Produces: `v*` 태그 push 시 GitHub 릴리스에 `YT-Launcher-Setup-<버전>.exe`, `SHA256SUMS.txt` 첨부 (updater가 기대하는 이름).

- [ ] **Step 1: CI 워크플로** — `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: windows-latest
    defaults:
      run:
        shell: pwsh
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - name: Install dependencies
        run: python -m pip install -e ".[dev]"
      - name: Test
        run: python -m pytest -q
```

- [ ] **Step 2: 릴리스 워크플로** — `.github/workflows/release.yml`

```yaml
name: Release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write

jobs:
  release:
    runs-on: windows-latest
    defaults:
      run:
        shell: pwsh
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - name: Install dependencies
        run: python -m pip install -e ".[dev]"
      - name: Test
        run: python -m pytest -q
      - name: Set version from tag
        run: |
          $version = "${{ github.ref_name }}".TrimStart("v")
          $file = "src/yt_launcher/version.py"
          (Get-Content $file -Raw) -replace '__version__ = "[^"]*"', "__version__ = `"$version`"" |
            Set-Content $file -Encoding utf8NoBOM -NoNewline
          "APP_VERSION=$version" | Out-File $env:GITHUB_ENV -Append -Encoding utf8
      - name: Install Inno Setup
        run: |
          if (-not (Test-Path "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe")) {
            choco install innosetup -y --no-progress
          }
      - name: Build installer
        run: ./scripts/build.ps1 -Version $env:APP_VERSION -Python python
      - name: Publish release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/installer/YT-Launcher-Setup-${{ env.APP_VERSION }}.exe
            dist/installer/SHA256SUMS.txt
          generate_release_notes: true
```

- [ ] **Step 3: 수동 점검표** — `docs/manual-test-checklist.md`

```markdown
# 릴리스 전 수동 점검표

빌드된 설치 프로그램으로 실제 Windows 11에서 확인한다.

## 런처 창
- [ ] 첫 실행 시 주 모니터 우상단(여백 16px)에 360×480으로 뜬다
- [ ] 작업표시줄에 아이콘이 없고 트레이 아이콘만 있다
- [ ] 다른 창을 열면 런처가 그 뒤로 깔린다
- [ ] 헤더 드래그로 이동, 가장자리/모서리 드래그로 크기 조절된다 (최소 240×200)
- [ ] "위치 잠금"을 켜면 이동·크기 조절이 안 된다
- [ ] 이동·크기 조절 후 재시작하면 그대로 복원된다
- [ ] "위치·크기 초기화"로 우상단 기본값으로 돌아간다
- [ ] Win+D(바탕화면 보기) 후에도 런처가 보인다. 안 보이면 트레이 아이콘 클릭으로 다시 나타난다 — 결과를 아래에 기록
- [ ] 보조 모니터로 옮긴 뒤 그 모니터를 분리하고 재시작하면 기본 위치로 돌아온다

## 타일
- [ ] ＋ → 검색어 입력 → 저장하면 타일이 생긴다 (이름 비우면 검색어 표시)
- [ ] 우클릭 → 수정/삭제(확인 대화상자)가 동작한다
- [ ] 드래그로 순서를 바꾸면 재시작 후에도 유지되고, ＋는 항상 마지막이다
- [ ] 크롬이 꺼진 상태에서 타일 클릭 → 최대화된 새 창(F11 아님)에 검색 결과
- [ ] 크롬이 켜진 상태에서 타일 클릭 → 기존 창에 새 탭, 그 창이 최대화되어 앞으로 온다
- [ ] 같은 타일을 빠르게 두 번 눌러도 탭이 하나만 열린다

## 설치·업데이트
- [ ] 설치 시 UAC 없이 설치되고 "설정 → 앱 → 설치된 앱"에 YT Launcher와 버전이 보인다
- [ ] "윈도우 시작 시 자동 실행" 체크 후 재부팅하면 런처가 자동으로 뜬다
- [ ] 트레이 메뉴의 자동 실행 토글을 끄면 재부팅 후 뜨지 않는다
- [ ] 더 높은 버전 릴리스 후 앱을 재시작하고 30초 뒤 "업데이트 있음 vX.Y.Z" 배지와 트레이 알림이 뜬다
- [ ] 배지 클릭 → 확인 → 진행 막대 → 런처 종료 → 자동 설치 → 런처 재실행 → "vX.Y.Z 버전으로 업데이트되었습니다" 알림
- [ ] 업데이트 후에도 타일·위치가 그대로다
- [ ] 제거 후 프로그램 폴더와 Run 값이 사라지고 `%APPDATA%\YT-Launcher`는 남는다

## 기록
- Windows 버전:
- Win+D 결과:
```

- [ ] **Step 4: README** — `README.md`

````markdown
# YT Launcher

바탕화면 우상단에 뜨는 타일형 런처. 타일을 누르면 크롬이 최대화 창으로 유튜브 검색 결과를 연다.

## 설치

[Releases](https://github.com/ssenu/YT-launcher/releases/latest)에서 `YT-Launcher-Setup-<버전>.exe`를 받아 실행한다.
코드 서명이 없어 처음에 "Windows의 PC 보호" 창이 뜨면 **추가 정보 → 실행**을 누른다.

## 개발

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m yt_launcher
```

로컬 설치 프로그램 빌드 (Inno Setup 6 필요): `./scripts/build.ps1`

## 릴리스

```powershell
git tag v0.2.0
git push origin v0.2.0
```

GitHub Actions가 테스트 → 빌드 → 릴리스 생성까지 한다. 설치된 앱은 하루 한 번 새 릴리스를 확인하고 "업데이트 있음" 배지를 띄운다.
릴리스 전에 `docs/manual-test-checklist.md`를 확인한다.
````

- [ ] **Step 5: 전체 테스트 후 Commit**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 실패 0

```powershell
git add .github docs/manual-test-checklist.md README.md
git commit -m "ci: add test and release workflows, docs"
```

- [ ] **Step 6: 첫 릴리스 (사용자 확인 후에만)**

외부에 게시되는 작업이므로 실행 전에 사용자에게 push와 태그 생성을 확인받는다. 승인되면:

```powershell
git push -u origin main
git tag v0.1.0
git push origin v0.1.0
gh run watch --exit-status
gh release view v0.1.0
```

Expected: Release 워크플로 성공, 릴리스 `v0.1.0`에 `YT-Launcher-Setup-0.1.0.exe`와 `SHA256SUMS.txt`가 첨부됨.

- [ ] **Step 7: 자동 업데이트 실전 확인 (사용자 확인 후에만)**

v0.1.0을 설치해 둔 상태에서 `v0.1.1` 태그를 같은 방식으로 push한다. 설치된 런처를 재시작하고 30초 뒤 배지가 뜨면 `docs/manual-test-checklist.md`의 "설치·업데이트" 항목을 따라 원클릭 업데이트를 확인한다.
