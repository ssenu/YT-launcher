"""런처 타일 데이터."""

from __future__ import annotations

import uuid
import zlib
from dataclasses import asdict, dataclass, field

# 채도를 낮춘 차분한 색 (테라코타, 더스티 로즈, 플럼, 더스티 블루, 스틸 블루, 세이지 틸, 세이지, 앰버)
PALETTE = (
    "#B5544C",
    "#B0577A",
    "#7E5A9B",
    "#4F6A9E",
    "#3F7F94",
    "#4E8A78",
    "#6E8F57",
    "#C07A45",
)

# v0.1.3 이전 원색 팔레트 → 같은 자리의 새 색 (저장된 타일 색을 그대로 옮긴다)
LEGACY_COLORS = dict(
    zip(
        ("#E53935", "#D81B60", "#8E24AA", "#3949AB", "#1E88E5", "#00897B", "#43A047", "#F4511E"),
        PALETTE,
    )
)


def migrate_color(color: str) -> str:
    return LEGACY_COLORS.get(color.upper(), color)


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
        return migrate_color(self.color) if self.color else auto_color(self.query)

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
