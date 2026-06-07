import pytest

from scalextric_optimizer.geometry import MissingGeometryError, Pose, compute_track_path
from scalextric_optimizer.parts import CurveGeometry, StraightGeometry, TrackPart


def synthetic_part(part_id, geometry):
    return TrackPart(
        id=part_id,
        name=part_id,
        type="test",
        verified_geometry=True,
        geometry=geometry,
    )


def test_simple_synthetic_sequence_has_deterministic_final_pose():
    parts = [
        synthetic_part("straight-10", StraightGeometry(length=10)),
        synthetic_part("left-quarter", CurveGeometry(radius=10, angle_degrees=90)),
        synthetic_part("straight-5", StraightGeometry(length=5)),
    ]

    path = compute_track_path(parts)

    assert len(path) == 4
    final_pose = path[-1]
    assert final_pose.x == pytest.approx(20.0)
    assert final_pose.y == pytest.approx(15.0)
    assert final_pose.heading_degrees == pytest.approx(90.0)


def test_can_start_from_custom_pose():
    part = synthetic_part("straight-3", StraightGeometry(length=3))

    path = compute_track_path([part], start=Pose(x=1, y=2, heading_degrees=90))

    assert path[-1].x == pytest.approx(1.0)
    assert path[-1].y == pytest.approx(5.0)
    assert path[-1].heading_degrees == pytest.approx(90.0)


def test_missing_geometry_raises_clear_error():
    part = TrackPart(
        id="unknown",
        name="Unknown geometry",
        type="straight",
        verified_geometry=False,
        geometry=None,
    )

    with pytest.raises(MissingGeometryError, match="does not have geometry"):
        compute_track_path([part])
