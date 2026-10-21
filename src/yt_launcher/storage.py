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
