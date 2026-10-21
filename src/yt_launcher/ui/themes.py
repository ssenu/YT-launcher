"""런처 창 테마(라이트·다크·세피아) 색상과 스타일시트."""

from __future__ import annotations

DEFAULT_THEME = "dark"

# 표시 순서 = 테마 메뉴 순서
THEME_LABELS = {
    "light": "라이트",
    "dark": "다크",
    "sepia": "세피아",
}

THEMES = {
    "dark": {
        "bg": "#16181D",
        "border": "#2A2E37",
        "header": "#1F232B",
        "title": "#F1F3F5",
        "byline": "#8A919C",
        "muted": "#C9CED6",
        "track": "#2A2E37",
        "add": "#2B2F3A",
    },
    "light": {
        "bg": "#F7F8FA",
        "border": "#D5D9E0",
        "header": "#FFFFFF",
        "title": "#1F232B",
        "byline": "#7A818C",
        "muted": "#4A5058",
        "track": "#E1E4E9",
        "add": "#A9AFB8",
    },
    "sepia": {
        "bg": "#F4ECD8",
        "border": "#D8C9A7",
        "header": "#EADFC4",
        "title": "#4B3A26",
        "byline": "#8C7656",
        "muted": "#5E4B33",
        "track": "#DCCDAA",
        "add": "#A8916B",
    },
}

_STYLE = """
#launcher {{ background: {bg}; border: 1px solid {border}; }}
#header {{ background: {header}; }}
#title {{ color: {title}; font-weight: bold; font-size: 13px; }}
#byline {{ color: {byline}; font-size: 10px; }}
#updateBadge {{ background: #E53935; color: #FFFFFF; border: none; border-radius: 9px;
               padding: 2px 10px; font-weight: bold; }}
#menuButton {{ color: {muted}; background: transparent; border: none; font-size: 16px; padding: 0 6px; }}
#menuButton::menu-indicator {{ image: none; }}
#themeButton {{ color: {muted}; background: transparent; border: none; font-size: 15px; padding: 0 4px; }}
#themeButton::menu-indicator {{ image: none; }}
#progress {{ background: {track}; border: none; }}
#progress::chunk {{ background: #E53935; }}
#tileGrid {{ background: transparent; border: none; }}
"""


def resolve_theme(name: str) -> str:
    """알 수 없는 테마 이름은 기본 테마로 바꾼다."""
    return name if name in THEMES else DEFAULT_THEME


def stylesheet(name: str) -> str:
    return _STYLE.format(**THEMES[resolve_theme(name)])


def add_tile_color(name: str) -> str:
    return THEMES[resolve_theme(name)]["add"]
