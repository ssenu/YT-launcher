"""패키지에 포함된 이미지·폰트 리소스."""

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QIcon

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
FONT_FAMILY = "Pretendard"
FONT_FILES = ("Pretendard-Regular.otf", "Pretendard-SemiBold.otf", "Pretendard-Bold.otf")
BASE_POINT_SIZE = 9.5


def asset_path(name: str) -> Path:
    return ASSETS_DIR / name


def app_icon() -> QIcon:
    return QIcon(str(asset_path("icon.png")))


def load_fonts() -> bool:
    """번들 폰트(Pretendard)를 등록한다. 하나라도 등록되면 True."""
    loaded = False
    for name in FONT_FILES:
        if QFontDatabase.addApplicationFont(str(asset_path(name))) != -1:
            loaded = True
    return loaded


def apply_app_font(app) -> None:
    """앱 기본 글꼴을 Pretendard로 바꾼다. 등록에 실패하면 시스템 글꼴을 그대로 쓴다."""
    if load_fonts():
        font = QFont(FONT_FAMILY)
        font.setPointSizeF(BASE_POINT_SIZE)
        font.setHintingPreference(QFont.PreferNoHinting)
        app.setFont(font)
