"""팔레트 버튼을 누르면 버튼 주위로 부채꼴처럼 펼쳐지는 테마 색 원 선택기."""

from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import themes

SWATCH_DIAMETER = 34
ARC_RADIUS = 64
# 버튼 중심 기준 각도 (Qt 좌표: 0°=오른쪽, -90°=위, 180°=왼쪽)
ARC_START_DEG = -90.0
ARC_END_DEG = -180.0
OPEN_MS = 160
HALO_ALPHA = 110
SELECTED_RING = "#E53935"


class ThemePicker(QWidget):
    """창 전체를 덮는 투명 오버레이. 빈 곳을 누르면 닫힌다."""

    picked = Signal(str)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setCursor(Qt.ArrowCursor)
        self.setMouseTracking(True)
        self.hide()
        self._names = list(themes.THEME_LABELS)
        self._current = themes.DEFAULT_THEME
        self._anchor = QPointF()
        self._progress = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(OPEN_MS)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_progress)

    @property
    def names(self) -> list[str]:
        return list(self._names)

    def open_at(self, anchor: QPointF, current: str) -> None:
        """anchor(창 좌표의 버튼 중심)를 기준으로 펼친다."""
        self._anchor = QPointF(anchor)
        self._current = current
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self._progress = 0.0
        self._anim.stop()
        self._anim.start()

    def close_picker(self) -> None:
        self._anim.stop()
        self.hide()

    def swatch_center(self, name: str, progress: float = 1.0) -> QPointF:
        index = self._names.index(name)
        step = (ARC_END_DEG - ARC_START_DEG) / max(len(self._names) - 1, 1)
        angle = math.radians(ARC_START_DEG + step * index)
        r = ARC_RADIUS * progress
        return QPointF(self._anchor.x() + r * math.cos(angle), self._anchor.y() + r * math.sin(angle))

    def name_at(self, pos: QPointF) -> str | None:
        for name in self._names:
            d = self.swatch_center(name, self._progress) - QPointF(pos)
            if math.hypot(d.x(), d.y()) <= SWATCH_DIAMETER / 2:
                return name
        return None

    def choose(self, name: str) -> None:
        self.close_picker()
        self.picked.emit(name)

    def _on_progress(self, value) -> None:
        self._progress = float(value)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        name = self.name_at(event.position())
        self.setToolTip(themes.THEME_LABELS[name] if name else "")
        self.setCursor(Qt.PointingHandCursor if name else Qt.ArrowCursor)

    def mousePressEvent(self, event) -> None:
        name = self.name_at(event.position())
        if name is None:
            self.close_picker()
        else:
            self.choose(name)
        event.accept()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        radius = SWATCH_DIAMETER / 2 * (0.6 + 0.4 * self._progress)
        # 바깥 테두리는 현재 창 테마의 글자색을 옅게 써서 어떤 배경에서도 원이 보이게 한다.
        halo = QColor(themes.THEMES[self._current]["muted"])
        halo.setAlpha(HALO_ALPHA)
        for name in self._names:
            colors = themes.THEMES[name]
            center = self.swatch_center(name, self._progress)
            p.setPen(Qt.NoPen)
            p.setBrush(halo)
            p.drawEllipse(center, radius + 4, radius + 4)
            ring = SELECTED_RING if name == self._current else colors["border"]
            p.setPen(QPen(QColor(ring), 2.5 if name == self._current else 1.5))
            p.setBrush(QColor(colors["bg"]))
            p.drawEllipse(center, radius, radius)
        p.end()
