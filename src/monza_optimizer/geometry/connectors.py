"""Connector model — male/female track ends and pose chaining."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from monza_optimizer.geometry.pose import Pose, normalize_heading


class ConnectorSide(Enum):
    """Physical Scalextric connector orientation along the driving direction."""

    ENTRY = "entry"   # where the previous piece attaches
    EXIT = "exit"     # where the next piece attaches


@dataclass(frozen=True)
class Connector:
    """A single track connector in world coordinates."""

    pose: Pose
    side: ConnectorSide
    part_id: str
    lane_count: int = 2

    def matches(self, other: Connector, pos_tol_mm: float = 2.0, head_tol_deg: float = 2.0) -> bool:
        """True if this exit can join the other entry (or vice versa)."""
        if self.side == other.side:
            return False
        dx = self.pose.x - other.pose.x
        dy = self.pose.y - other.pose.y
        if math.hypot(dx, dy) > pos_tol_mm:
            return False
        # Exit heading should align with entry heading
        dh = abs(normalize_heading(self.pose.heading_degrees - other.pose.heading_degrees))
        return dh <= head_tol_deg


def connect_poses(exit_pose: Pose, entry_offset: Pose | None = None) -> Pose:
    """Place the next piece so its entry coincides with the previous exit.

    entry_offset is reserved for parts whose local origin is not at the entry.
    """
    if entry_offset is None:
        return exit_pose
    # Rotate offset by exit heading and translate
    hr = math.radians(exit_pose.heading_degrees)
    c, s = math.cos(hr), math.sin(hr)
    dx = entry_offset.x * c - entry_offset.y * s
    dy = entry_offset.x * s + entry_offset.y * c
    return Pose(
        exit_pose.x + dx,
        exit_pose.y + dy,
        normalize_heading(exit_pose.heading_degrees + entry_offset.heading_degrees),
    )
