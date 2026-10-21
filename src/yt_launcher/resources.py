"""패키지에 포함된 이미지 리소스."""

from pathlib import Path

from PySide6.QtGui import QIcon

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def asset_path(name: str) -> Path:
    return ASSETS_DIR / name


def app_icon() -> QIcon:
    return QIcon(str(asset_path("icon.png")))
