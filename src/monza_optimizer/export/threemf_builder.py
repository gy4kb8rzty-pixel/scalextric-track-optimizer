"""Lean 3MF builder for Microsoft 3D Builder.

Assembles track piece meshes, optional red outline tube, ground plane,
and colour-key legend with part numbers. Designed for low triangle count
so 3D Builder does not hang on repair.
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
    "C8010": "3498DB",
}
OUTLINE_COLOR = "E53935"
GROUND_COLOR = "455A64"
LEGEND_BG = "212121"


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


def _curve_mesh(part, code: str, half_w: float = 78.0, h: float = 8.0, steps: int = 6, z0: float = 10.0):
    ang = _signed_angle(part, code)
    R = part.geometry.radius
    n = max(3, steps)
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
    verts = []
    for pose in stations:
        hr = math.radians(pose.heading_degrees)
        nx, ny = -math.sin(hr), math.cos(hr)
        verts += [
            (pose.x + nx * half_w, pose.y + ny * half_w, z0),
            (pose.x - nx * half_w, pose.y - ny * half_w, z0),
            (pose.x + nx * half_w, pose.y + ny * half_w, z0 + h),
            (pose.x - nx * half_w, pose.y - ny * half_w, z0 + h),
        ]
    tris = []
    for i in range(len(stations) - 1):
        a, b = 4 * i, 4 * (i + 1)
        tris += [
            (a + 2, b + 2, b + 3), (a + 2, b + 3, a + 3),
            (a, a + 1, b + 1), (a, b + 1, b),
            (a, a + 2, b + 2), (a, b + 2, b),
            (a + 1, b + 1, b + 3), (a + 1, b + 3, a + 3),
        ]
    return verts, tris


def _straight_mesh(part, half_w: float = 78.0, h: float = 8.0, z0: float = 10.0):
    L = part.geometry.length
    verts = [
        (0, -half_w, z0), (L, -half_w, z0), (L, half_w, z0), (0, half_w, z0),
        (0, -half_w, z0 + h), (L, -half_w, z0 + h), (L, half_w, z0 + h), (0, half_w, z0 + h),
    ]
    tris = [
        (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
        (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
        (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
    ]
    return verts, tris


def _xform(verts, pose: Pose):
    hr = math.radians(pose.heading_degrees)
    c, s = math.cos(hr), math.sin(hr)
    return [(pose.x + x * c - y * s, pose.y + x * s + y * c, z) for x, y, z in verts]


def _box_mesh(x0, y0, x1, y1, z0, z1):
    verts = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    tris = [
        (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
        (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
        (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
    ]
    return verts, tris


def _tube_mesh(pts, radius: float = 12.0, z0: float = 30.0, sides: int = 6, step: float = 60.0):
    dens = [pts[0]]
    for i in range(1, len(pts)):
        x0, y0 = dens[-1]
        x1, y1 = pts[i]
        d = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(d / step))
        for k in range(1, n + 1):
            t = k / n
            dens.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    if len(dens) > 2200:
        dens = dens[:: max(1, len(dens) // 1800)]
    verts = []
    tris = []
    for i, (x, y) in enumerate(dens):
        if i < len(dens) - 1:
            dx, dy = dens[i + 1][0] - x, dens[i + 1][1] - y
        else:
            dx, dy = x - dens[i - 1][0], y - dens[i - 1][1]
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L
        for si in range(sides):
            ang = 2 * math.pi * si / sides
            verts.append(
                (
                    x + radius * math.cos(ang) * px,
                    y + radius * math.cos(ang) * py,
                    z0 + radius * math.sin(ang),
                )
            )
    for i in range(len(dens) - 1):
        for si in range(sides):
            a = i * sides + si
            b = i * sides + (si + 1) % sides
            c = (i + 1) * sides + (si + 1) % sides
            d = (i + 1) * sides + si
            tris.append((a, b, c))
            tris.append((a, c, d))
    return verts, tris


def build_track_3mf(
    sequence: Sequence[str],
    get_part: Callable,
    out_path: str | Path,
    *,
    outline_points: Sequence[tuple[float, float]] | None = None,
    title: str = "Scalextric track",
    track_z: float = 10.0,
    tube_z: float = 30.0,
    include_legend: bool = True,
) -> Path:
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
    ensure(OUTLINE_COLOR)
    ensure(GROUND_COLOR)
    ensure(LEGEND_BG)
    ensure("FFFFFF")

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

    xs = [p.x for p in poses]
    ys = [p.y for p in poses]
    if outline_points:
        xs += [c[0] for c in outline_points]
        ys += [c[1] for c in outline_points]
        tv, tt = _tube_mesh(list(outline_points), z0=tube_z)
        vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in tv)
        txml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a, b, c in tt)
        pi = ensure(OUTLINE_COLOR)
        objects.append(
            f'<object id="{oid}" name="Official_outline" type="model" pid="1" pindex="{pi}">'
            f"<mesh><vertices>{vxml}</vertices><triangles>{txml}</triangles></mesh></object>"
        )
        items.append(f'<item objectid="{oid}" />')
        oid += 1

    minx, maxx = min(xs) - 200, max(xs) + 200
    miny, maxy = min(ys) - 200, max(ys) + 200
    gv, gt = _box_mesh(minx, miny, maxx, maxy, -2, 0)
    vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in gv)
    txml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a, b, c in gt)
    pi = ensure(GROUND_COLOR)
    objects.append(
        f'<object id="{oid}" name="ground_plane" type="model" pid="1" pindex="{pi}">'
        f"<mesh><vertices>{vxml}</vertices><triangles>{txml}</triangles></mesh></object>"
    )
    items.append(f'<item objectid="{oid}" />')
    oid += 1

    if include_legend:
        used_bases = sorted({base_id(c) for c in codes})
        legend = [(b, PART_COLORS.get(b, "888")) for b in used_bases]
        n_leg = max(len(legend), 1)
        sw, sh, gap, pad = 150.0, 50.0, 12.0, 24.0
        leg_h = pad * 2 + n_leg * (sh + gap) - gap
        leg_w = pad * 2 + sw + 20
        leg_x0, leg_y0 = maxx + 100, miny
        bg, bgt = _box_mesh(leg_x0, leg_y0, leg_x0 + leg_w, leg_y0 + leg_h, 0, 4)
        vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in bg)
        txml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a, b, c in bgt)
        pi = ensure(LEGEND_BG)
        objects.append(
            f'<object id="{oid}" name="COLOR_KEY_PANEL" type="model" pid="1" pindex="{pi}">'
            f"<mesh><vertices>{vxml}</vertices><triangles>{txml}</triangles></mesh></object>"
        )
        items.append(f'<item objectid="{oid}" />')
        oid += 1
        for i, (key, col) in enumerate(legend):
            sy0 = leg_y0 + pad + i * (sh + gap)
            sx0 = leg_x0 + pad
            sv, st = _box_mesh(sx0, sy0, sx0 + sw, sy0 + sh, 4, 10)
            vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in sv)
            txml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a, b, c in st)
            pi = ensure(col)
            objects.append(
                f'<object id="{oid}" name="KEY_{key}" type="model" pid="1" pindex="{pi}">'
                f"<mesh><vertices>{vxml}</vertices><triangles>{txml}</triangles></mesh></object>"
            )
            items.append(f'<item objectid="{oid}" />')
            oid += 1

    bases = "".join(
        f'<base name="mat{i}" displaycolor="#{col}" />' for i, col in enumerate(color_list)
    )
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<metadata name="Title">{title}</metadata>'
        f'<resources><basematerials id="1">{bases}</basematerials>'
        f'{ "".join(objects) }</resources>'
        f'<build>{ "".join(items) }</build></model>'
    )
    ct = (
        '<?xml version="1.0"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0"?>'
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
