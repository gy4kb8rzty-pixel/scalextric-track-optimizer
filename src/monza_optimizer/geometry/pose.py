"""Pose and heading utilities."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Pose:
    """World-frame placement of a track connector or piece origin."""

    x: float
    y: float
    heading_degrees: float

    def translated(self, dx: float, dy: float) -> Pose:
        return Pose(self.x + dx, self.y + dy, self.heading_degrees)

    def rotated(self, delta_degrees: float) -> Pose:
        return Pose(self.x, self.y, normalize_heading(self.heading_degrees + delta_degrees))


def normalize_heading(degrees: float) -> float:
    """Map heading into (-180, 180]."""
    h = degrees % 360.0
    if h > 180.0:
        h -= 360.0
    return h


def heading_delta(a: float, b: float) -> float:
    """Signed shortest delta from heading a to b."""
    return normalize_heading(b - a)


def distance(a: Pose, b: Pose) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)
