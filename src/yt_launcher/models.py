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
