"""Geometry validation — never bypass for optimization scores.

Closure tolerances may include a physical elasticity allowance so that
small residuals absorbable by joint play on long layouts are accepted.
Elasticity never overrides missing geometry, lane errors, or connector
mismatches.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from monza_optimizer.geometry.elasticity import ElasticityModel, DEFAULT_ELASTICITY
from monza_optimizer.geometry.lanes import LaneTopology, validate_lane_continuity
from monza_optimizer.geometry.path import (
    compute_track_path,
    closure_error,
    is_closed,
    path_length,
)
from monza_optimizer.geometry.pose import Pose


class GeometryValidationError(ValueError):
    """Raised when a layout fails mandatory geometry checks."""


@dataclass
class GeometryValidator:
    """Hard validation gate for layouts.

    When ``elasticity`` is set (default), position/heading closure
    tolerances scale with path length. Rigid mode: pass
    ``elasticity=None`` and use ``pos_tol_mm`` / ``head_tol_deg`` only.
    """

    pos_tol_mm: float = 5.0
    head_tol_deg: float = 2.0
    require_closed: bool = True
    require_verified_geometry: bool = True
    elasticity: ElasticityModel | None = field(default_factory=lambda: DEFAULT_ELASTICITY)
    issues: list[str] = field(default_factory=list)

    def effective_tolerances(self, path_length_mm: float) -> tuple[float, float]:
        """Return (pos_tol_mm, head_tol_deg) for this layout length."""
        if self.elasticity is not None:
            return (
                self.elasticity.position_tolerance_mm(path_length_mm),
                self.elasticity.heading_tolerance_deg(),
            )
        return self.pos_tol_mm, self.head_tol_deg

    def validate_parts(self, parts: list) -> list[str]:
        issues: list[str] = []
        for i, part in enumerate(parts):
            if part.geometry is None:
                issues.append(f"piece {i} ({part.id}): missing geometry")
            elif self.require_verified_geometry and not getattr(part, "verified_geometry", True):
                issues.append(f"piece {i} ({part.id}): geometry not verified")
        return issues

    def validate_path(self, parts: list, start: Pose | None = None) -> list[str]:
        issues = self.validate_parts(parts)
        if issues:
            return issues
        path = compute_track_path(parts, start=start)
        pos_err, head_err = closure_error(path)
        length = path_length(parts)
        pos_tol, head_tol = self.effective_tolerances(length)
        if self.require_closed and not is_closed(path, pos_tol, head_tol):
            extra = ""
            if self.elasticity is not None:
                extra = f" [{self.elasticity.describe(length)}]"
            issues.append(
                f"not closed: pos_err={pos_err:.2f} mm head_err={head_err:.2f}° "
                f"(tol {pos_tol:.2f} mm / {head_tol:.2f}°){extra}"
            )
        return issues

    def accepts_closure(
        self,
        pos_err_mm: float,
        head_err_deg: float,
        path_length_mm: float,
    ) -> bool:
        """True if residual is within elastic (or rigid) tolerances."""
        pos_tol, head_tol = self.effective_tolerances(path_length_mm)
        return pos_err_mm <= pos_tol and head_err_deg <= head_tol

    def validate_lanes(self, topologies: list[LaneTopology]) -> list[str]:
        return validate_lane_continuity(topologies)

    def assert_valid(self, parts: list, start: Pose | None = None) -> None:
        issues = self.validate_path(parts, start=start)
        if issues:
            raise GeometryValidationError("; ".join(issues))
