"""Track path computation from ordered parts."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from monza_optimizer.geometry.pose import Pose, normalize_heading

if TYPE_CHECKING:
    from monza_optimizer.catalog.parts import TrackPart
    from monza_optimizer.catalog.geometry_types import StraightGeometry, CurveGeometry


class MissingGeometryError(ValueError):
    pass


def compute_track_path(parts: list, start: Pose | None = None) -> list[Pose]:
    """Return poses at the entry of each piece plus final exit pose."""
    current = start if start is not None else Pose(0.0, 0.0, 0.0)
    path = [current]
    for part in parts:
        current = _advance(current, part)
        path.append(current)
    return path


def _advance(pose: Pose, part) -> Pose:
    geometry = part.geometry
    if geometry is None:
        raise MissingGeometryError(f"part '{part.id}' does not have geometry")
    from monza_optimizer.catalog.geometry_types import StraightGeometry, CurveGeometry

    if isinstance(geometry, StraightGeometry):
        return _advance_straight(pose, geometry.length)
    if isinstance(geometry, CurveGeometry):
        angle = geometry.angle_degrees
        # Honour L/R suffix if angle stored as absolute
        pid = getattr(part, "id", "")
        if pid.endswith("R") and angle > 0:
            angle = -angle
        elif pid.endswith("L") and angle < 0:
            angle = -angle
        return _advance_curve(pose, geometry.radius, angle)
    raise MissingGeometryError(f"part '{part.id}' has unsupported geometry")


def _advance_straight(pose: Pose, length: float) -> Pose:
    hr = math.radians(pose.heading_degrees)
    return Pose(
        pose.x + length * math.cos(hr),
        pose.y + length * math.sin(hr),
        pose.heading_degrees,
    )


def _advance_curve(pose: Pose, radius: float, angle_degrees: float) -> Pose:
    hr = math.radians(pose.heading_degrees)
    ar = math.radians(angle_degrees)
    td = 1.0 if angle_degrees >= 0 else -1.0
    lx = radius * math.sin(abs(ar))
    ly = td * radius * (1.0 - math.cos(abs(ar)))
    wx = lx * math.cos(hr) - ly * math.sin(hr)
    wy = lx * math.sin(hr) + ly * math.cos(hr)
    return Pose(pose.x + wx, pose.y + wy, pose.heading_degrees + angle_degrees)


def path_length(parts: list) -> float:
    total = 0.0
    from monza_optimizer.catalog.geometry_types import StraightGeometry, CurveGeometry

    for part in parts:
        g = part.geometry
        if g is None:
            raise MissingGeometryError(f"part '{part.id}' does not have geometry")
        if isinstance(g, StraightGeometry):
            total += g.length
        elif isinstance(g, CurveGeometry):
            total += abs(math.radians(g.angle_degrees)) * g.radius
        else:
            raise MissingGeometryError(f"part '{part.id}' has unsupported geometry")
    return total


def closure_error(path: list[Pose]) -> tuple[float, float]:
    if len(path) < 2:
        return 0.0, 0.0
    start, end = path[0], path[-1]
    pos_err = math.hypot(end.x - start.x, end.y - start.y)
    head_err = abs(normalize_heading(end.heading_degrees - start.heading_degrees))
    return pos_err, head_err


def is_closed(path: list[Pose], pos_tol_mm: float = 5.0, head_tol_deg: float = 2.0) -> bool:
    pos_err, head_err = closure_error(path)
    return pos_err <= pos_tol_mm and head_err <= head_tol_deg


def bounding_box(path: list[Pose]) -> tuple[float, float, float, float]:
    xs = [p.x for p in path]
    ys = [p.y for p in path]
    return min(xs), min(ys), max(xs), max(ys)
