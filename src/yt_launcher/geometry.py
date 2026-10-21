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