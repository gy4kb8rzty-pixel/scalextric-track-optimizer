"""Physical elasticity of Scalextric track joints.

Real plastic pieces absorb small closure residuals through joint play and
flex. On a ~15 m inventory layout, residuals on the order of 15–25 mm are
routinely manageable without forcing pieces.

The model is intentionally simple and conservative:

    pos_tol = max(pos_tol_min, elastic_fraction * path_length)
    head_tol = max(head_tol_min, elastic_heading_deg)

Defaults are chosen so that ~18 mm on a 15 m track is accepted, while a
0.5 m gap on the same track is not.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ElasticityModel:
    """Length-dependent closure tolerance from joint elasticity.

    Parameters
    ----------
    elastic_fraction:
        Allowed position residual as a fraction of centreline length.
        0.0015 → 1.5 mm per metre ≈ 22.5 mm on 15 m.
    pos_tol_min_mm:
        Floor so very short loops still have a usable tolerance.
    pos_tol_max_mm:
        Cap so elasticity never excuses large gaps on long tracks.
    head_tol_deg:
        Heading residual absorbed by joint twist (degrees).
    """

    elastic_fraction: float = 0.0015
    pos_tol_min_mm: float = 8.0
    pos_tol_max_mm: float = 30.0
    head_tol_deg: float = 2.5

    def position_tolerance_mm(self, path_length_mm: float) -> float:
        if path_length_mm < 0:
            raise ValueError("path_length_mm must be non-negative")
        tol = self.elastic_fraction * path_length_mm
        return float(min(self.pos_tol_max_mm, max(self.pos_tol_min_mm, tol)))

    def heading_tolerance_deg(self) -> float:
        return float(self.head_tol_deg)

    def is_closed(
        self,
        pos_err_mm: float,
        head_err_deg: float,
        path_length_mm: float,
    ) -> bool:
        return (
            pos_err_mm <= self.position_tolerance_mm(path_length_mm)
            and head_err_deg <= self.heading_tolerance_deg()
        )

    def describe(self, path_length_mm: float) -> str:
        return (
            f"elasticity: pos_tol={self.position_tolerance_mm(path_length_mm):.1f} mm "
            f"(fraction={self.elastic_fraction}, clamp "
            f"[{self.pos_tol_min_mm}, {self.pos_tol_max_mm}]) "
            f"head_tol={self.heading_tolerance_deg():.1f}°"
        )


# Default model used by the optimizer unless a profile overrides it.
DEFAULT_ELASTICITY = ElasticityModel()
