"""Geometry engine: poses, connectors, lanes, path computation, validation."""

from monza_optimizer.geometry.pose import Pose, normalize_heading
from monza_optimizer.geometry.connectors import Connector, ConnectorSide, connect_poses
from monza_optimizer.geometry.lanes import LaneTopology, validate_lane_continuity
from monza_optimizer.geometry.path import (
    compute_track_path,
    path_length,
    closure_error,
    is_closed,
    bounding_box,
)
from monza_optimizer.geometry.validation import GeometryValidator, GeometryValidationError
from monza_optimizer.geometry.elasticity import ElasticityModel, DEFAULT_ELASTICITY

__all__ = [
    "Pose",
    "normalize_heading",
    "Connector",
    "ConnectorSide",
    "connect_poses",
    "LaneTopology",
    "validate_lane_continuity",
    "compute_track_path",
    "path_length",
    "closure_error",
    "is_closed",
    "bounding_box",
    "GeometryValidator",
    "GeometryValidationError",
    "ElasticityModel",
    "DEFAULT_ELASTICITY",
]
