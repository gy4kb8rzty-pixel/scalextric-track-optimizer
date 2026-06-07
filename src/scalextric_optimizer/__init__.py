"""Phase 1 foundation for a generic Scalextric track optimizer."""

from .geometry import Pose, compute_track_path
from .parts import CurveGeometry, PartValidationError, StraightGeometry, TrackPart, load_parts

__all__ = [
    "CurveGeometry",
    "PartValidationError",
    "Pose",
    "StraightGeometry",
    "TrackPart",
    "compute_track_path",
    "load_parts",
]
