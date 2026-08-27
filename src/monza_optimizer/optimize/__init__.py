"""Pareto optimization and construction strategies."""

from monza_optimizer.optimize.hypervolume import (
    hypervolume,
    hypervolume_2d,
    filter_non_dominated,
    dominates,
)
from monza_optimizer.optimize.corner_first import (
    Centreline,
    densify_polyline,
    detect_corners,
    place_all_anchors,
    fill_gap,
    local_window_reopt,
    corner_first_build,
    CornerFirstResult,
)
from monza_optimizer.optimize.sequential import sequential_follow, SequentialResult
from monza_optimizer.optimize.coverage_fill import coverage_fill, coverage_distances, find_uncovered_segments

__all__ = [
    "hypervolume",
    "hypervolume_2d",
    "filter_non_dominated",
    "dominates",
    "Centreline",
    "densify_polyline",
    "detect_corners",
    "place_all_anchors",
    "fill_gap",
    "local_window_reopt",
    "corner_first_build",
    "CornerFirstResult",
    "sequential_follow",
    "SequentialResult",
    "coverage_fill",
    "coverage_distances",
    "find_uncovered_segments",
]
