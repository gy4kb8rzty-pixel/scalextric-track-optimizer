"""Parametric geometry types for Scalextric pieces."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StraightGeometry:
    length: float  # mm along centreline


@dataclass(frozen=True)
class CurveGeometry:
    radius: float  # mm centreline radius
    angle_degrees: float  # signed: +CCW/left, -CW/right


Geometry = StraightGeometry | CurveGeometry
