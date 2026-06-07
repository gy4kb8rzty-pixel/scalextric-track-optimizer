"""Basic geometry primitives for track path calculations."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .parts import CurveGeometry, StraightGeometry, TrackPart


@dataclass(frozen=True)
class Pose:
    """A 2D position and heading in degrees."""

    x: float
    y: float
    heading_degrees: float


class MissingGeometryError(ValueError):
    """Raised when path calculation needs geometry that is unavailable."""


def compute_track_path(parts: list[TrackPart], start: Pose | None = None) -> list[Pose]:
    """Compute poses after each part in sequence.

    The returned list includes the start pose as the first item. Every part in
    the sequence must have geometry; the inventory may intentionally leave real
    Scalextric geometry unknown until it is verified.
    """

    current = start or Pose(x=0.0, y=0.0, heading_degrees=0.0)
    path = [current]

    for part in parts:
        if part.geometry is None:
            raise MissingGeometryError(f"part '{part.id}' does not have geometry")
        current = _advance(current, part)
        path.append(current)

    return path


def _advance(pose: Pose, part: TrackPart) -> Pose:
    geometry = part.geometry
    if isinstance(geometry, StraightGeometry):
        return _advance_straight(pose, geometry.length)
    if isinstance(geometry, CurveGeometry):
        return _advance_curve(pose, geometry.radius, geometry.angle_degrees)
    raise MissingGeometryError(f"part '{part.id}' has unsupported geometry")


def _advance_straight(pose: Pose, length: float) -> Pose:
    heading_radians = math.radians(pose.heading_degrees)
    return Pose(
        x=pose.x + length * math.cos(heading_radians),
        y=pose.y + length * math.sin(heading_radians),
        heading_degrees=pose.heading_degrees,
    )


def _advance_curve(pose: Pose, radius: float, angle_degrees: float) -> Pose:
    heading_radians = math.radians(pose.heading_degrees)
    arc_radians = math.radians(angle_degrees)
    turn_direction = 1.0 if angle_degrees >= 0 else -1.0

    local_x = radius * math.sin(abs(arc_radians))
    local_y = turn_direction * radius * (1.0 - math.cos(abs(arc_radians)))

    world_x = local_x * math.cos(heading_radians) - local_y * math.sin(heading_radians)
    world_y = local_x * math.sin(heading_radians) + local_y * math.cos(heading_radians)

    return Pose(
        x=pose.x + world_x,
        y=pose.y + world_y,
        heading_degrees=pose.heading_degrees + angle_degrees,
    )
