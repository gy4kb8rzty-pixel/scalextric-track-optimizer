"""Lean 3MF for Microsoft 3D Builder.

Only watertight piece solids. No ground plane or open legend slab.
"""

from __future__ import annotations

import math
import zipfile
from pathlib import Path
from typing import Callable, Sequence

from monza_optimizer.catalog.geometry_types import CurveGeometry
from monza_optimizer.catalog.parts import base_id
from monza_optimizer.geometry.pose import Pose
from monza_optimizer.geometry.path import compute_track_path

PART_COLORS = {
    "C8205": "808890",
    "C8207": "B0B8C0",
    "C8200": "D0D8E0",
    "C8236": "F1C40F",
    "C8204": "2E86DE",
    "C8206": "27AE60",
    "C8235": "E67E22",
    "C187": "8E44AD",
    "C8234": "1ABC9C",
    "C156": "C0392B",
    "C8201": "C0392B",
    "C8010": "3498DB",
}


def _signed_angle(part, code: str) -> float:
    if not isinstance(part.geometry, CurveGeometry):
        return 0.0
    a = abs(part.geometry.angle_degrees)
    pid = code or getattr(part, "id", "")
    if pid.endswith("R"):
        return -a
    if pid.endswith("L"):
        return a
    return float(part.geometry.angle_degrees)


def _ring(pose: Pose, half_w: float, z0: float, h: float):
    hr = math.radians(pose.heading_degrees)
    nx, ny = -math.sin(hr), math.cos(hr)
    return [
        (pose.x + nx * half_w, pose.y + ny * half_w, z0),
        (pose.x - nx * half_w, pose.y - ny * half_w, z0),
        (pose.x + nx * half_w, pose.y + ny * half_w, z0 + h),
        (pose.x - nx * half_w, pose.y - ny * half_w, z0 + h),
    ]


def _curve_mesh(part, code: str, half_w: float = 78.0, h: float = 8.0, steps: int = 8, z0: float = 0.0):
    ang = _signed_angle(part, code)
    R = part.geometry.radius
    n = max(4, steps)
    pose = Pose(0, 0, 0)
    stations = [pose]
    dt = ang / n
    for _ in range(n):
        ar = math.radians(dt)
        hr = math.radians(pose.heading_degrees)
        td = 1.0 if dt >= 0 else -1.0
        lx = R * math.sin(abs(ar))
        ly = td * R * (1 - math.cos(abs(ar)))
        wx = lx * math.cos(hr) - ly * math.sin(hr)
        wy = lx * math.sin(hr) + ly * math.cos(hr)
        pose = Pose(pose.x + wx, pose.y + wy, pose.heading_degrees + dt)
        stations.append(pose)
    verts: list[tuple[float, float, float]] = []
    for st in stations:
        verts.extend(_ring(st, half_w, z0, h))
    tris: list[tuple[int, int, int]] = []
    for i in range(len(stations) - 1):
        a, b = 4 * i, 4 * (i + 1)
        tris += [(a + 2, b + 2, b + 3), (a + 2, b + 3, a + 3)]
        tris += [(a, a + 1, b + 1), (a, b + 1, b)]
        tris += [(a, a + 2, b + 2), (a, b + 2, b)]
        tris += [(a + 1, b + 1, b + 3), (a + 1, b + 3, a + 3)]
    s = 0
    e = 4 * (len(stations) - 1)
    tris += [(s, s + 2, s + 3), (s, s + 3, s + 1)]
    tris += [(e, e + 1, e + 3), (e, e + 3, e + 2)]
    return verts, tris


def _straight_mesh(part, half_w: float = 78.0, h: float = 8.0, z0: float = 0.0):
    L = part.geometry.length
    verts = [
        (0, -half_w, z0), (L, -half_w, z0), (L, half_w, z0), (0, half_w, z0),
        (0, -half_w, z0 + h), (L, -half_w, z0 + h), (L, half_w, z0 + h), (0, half_w, z0 + h),
    ]n    tris = [
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (3, 7, 6), (3, 6, 2),
        (0, 4, 7), (0, 7, 3),
        (1, 2, 6), (1, 6, 5),
    ]
    return verts, tris


def _xform(verts, pose: Pose):
    hr = math.radians(pose.heading_degrees)
    c, s = math.cos(hr), math.sin(hr)
    return [(pose.x + x * c - y * s, pose.y + x * s + y * c, z) for x, y, z in verts]


def build_track_3mf(
    sequence: Sequence[str],
    get_part: Callable,
    out_path: str | Path,
    *,
    outline_points: Sequence[tuple[float, float]] | None = None,
    title: str = "Scalextric track",
    track_z: float = 0.0,
    tube_z: float = 30.0,
    include_legend: bool = False,
    include_ground: bool = False,
) -> Path:
    del outline_points, tube_z, include_legend, include_ground
    out_path = Path(out_path)
    codes = [c for c in sequence if get_part(c) is not None]
    parts = [get_part(c) for c in codes]
    poses = compute_track_path(parts, start=Pose(0.0, 0.0, 0.0)) if parts else [Pose(0, 0, 0)]

    color_list: list[str] = []
    color_index: dict[str, int] = {}

    def ensure(col: str) -> int:
        if col not in color_index:
            color_index[col] = len(color_list)
            color_list.append(col)
        return color_index[col]

    def color_for(code: str) -> str:
        return PART_COLORS.get(base_id(code), "7F8C8D")

    for code in codes:
        ensure(color_for(code))
    if not color_list:
        ensure("7F8C8D")

    objects: list[str] = []
    items: list[str] = []
    oid = 2
    for i, code in enumerate(codes):
        part = parts[i]
        pose0 = poses[i]
        if isinstance(part.geometry, CurveGeometry):
            lv, lt = _curve_mesh(part, code, z0=track_z)
        else:
            lv, lt = _straight_mesh(part, z0=track_z)
        wv = _xform(lv, pose0)
        vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in wv)
        txml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a, b, c in lt)
        pi = ensure(color_for(code))
        objects.append(
            f'<object id="{oid}" name="{code}_{i+1}" type="model" pid="1" pindex="{pi}">'
            f"<mesh><vertices>{vxml}</vertices><triangles>{txml}</triangles></mesh></object>"
        )
        items.append(f'<item objectid="{oid}" />')
        oid += 1

    bases = "".join(
        f'<base name="mat{i}" displaycolor="#{col}FF" />' for i, col in enumerate(color_list)
    )
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<metadata name="Title">{title}</metadata>'
        '<metadata name="Description">Colour: grey straight, yellow short, green R2, blue R3, orange R4, red R1</metadata>'
        f'<resources><basematerials id="1">{bases}</basematerials>'
        f'{ "".join(objects) }</resources>'
        f'<build>{ "".join(items) }</build></model>'
    )
    ct = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    return out_path
