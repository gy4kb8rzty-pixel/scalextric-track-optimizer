"""3MF for Microsoft 3D Builder: coloured pieces plus red guide centreline."""

from __future__ import annotations

import math
import zipfile
from pathlib import Path
from typing import Callable, Sequence

from monza_optimizer.catalog.geometry_types import CurveGeometry
from monza_optimizer.catalog.parts import base_id
from monza_optimizer.geometry.pose import Pose
from monza_optimizer.geometry.path import compute_track_path, path_length

PART_COLORS = {
    "C8205": "808890",
    "C8207": "B0B8C0",
    "C8200": "D0D8E0",
    "C8236": "F1C40F",
    "C8204": "2E86DE",
    "C8206": "27AE60",
    "C8235": "E67E22",
    "C187": "FFFFFF",
    "C8234": "1ABC9C",
    "C156": "C0392B",
    "C8201": "C0392B",
    "C8202": "E91E63",
    "C8203": "6C3483",
    "C8010": "5DADE2",
}
GUIDE_COLOR = "C0392B"
RULER_COLOR = "2C3E50"


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


def _heading_of(outline: Sequence[tuple[float, float]]) -> float:
    if not outline or len(outline) < 2:
        return 0.0
    x0, y0 = outline[0]
    x1, y1 = outline[1]
    return math.degrees(math.atan2(y1 - y0, x1 - x0))


def _poly_len(pts: Sequence[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(pts) - 1):
        total += math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
    return total


def _fit_outline(outline: Sequence[tuple[float, float]], built_mm: float):
    pts = [(float(x), float(y)) for x, y in outline]
    if len(pts) < 2 or built_mm < 1.0:
        return pts
    L = _poly_len(pts)
    if L < 1.0:
        return pts
    s = built_mm / L
    x0, y0 = pts[0]
    return [((x - x0) * s + x0, (y - y0) * s + y0) for x, y in pts]


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
        hr = math.radians(pose.heading_degrees)
        ar = math.radians(dt)
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
    ]
    tris = [
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (3, 7, 6), (3, 6, 2),
        (0, 4, 7), (0, 7, 3),
        (1, 2, 6), (1, 6, 5),
    ]
    return verts, tris


def _box_mesh(x0, y0, x1, y1, z0=0.0, z1=10.0):
    verts = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    tris = [
        (0, 1, 2), (0, 2, 3),
        (4, 6, 5), (4, 7, 6),
        (0, 4, 5), (0, 5, 1),
        (1, 5, 6), (1, 6, 2),
        (2, 6, 7), (2, 7, 3),
        (3, 7, 4), (3, 4, 0),
    ]
    return verts, tris


def _ruler_step(span_mm: float) -> float:
    if span_mm < 4000:
        return 500.0
    if span_mm < 9000:
        return 1000.0
    if span_mm < 18000:
        return 2000.0
    if span_mm < 40000:
        return 5000.0
    return 10000.0


def _ruler_meshes(xs: list[float], ys: list[float]):
    if not xs or not ys:
        return [], []
    pad = 200.0
    xmin, xmax = min(xs) - pad, max(xs) + pad
    ymin, ymax = min(ys) - pad, max(ys) + pad
    wx, wy = max(1.0, xmax - xmin), max(1.0, ymax - ymin)
    sx, sy = _ruler_step(wx), _ruler_step(wy)
    thick, h, tick = 16.0, 8.0, 90.0
    gap = 220.0
    verts: list = []
    tris: list = []

    def add(v, t):
        off = len(verts)
        verts.extend(v)
        tris.extend((a + off, b + off, c + off) for a, b, c in t)

    yb = ymin - gap
    x1 = xmin + sx * max(1, int(round(wx / sx)))
    add(*_box_mesh(xmin, yb - thick / 2, x1, yb + thick / 2, 0.0, h))
    x = xmin
    while x <= x1 + 0.5:
        add(*_box_mesh(x - thick / 2, yb - tick, x + thick / 2, yb + thick / 2, 0.0, h + 3))
        x += sx
    xl = xmin - gap
    y1 = ymin + sy * max(1, int(round(wy / sy)))
    add(*_box_mesh(xl - thick / 2, ymin, xl + thick / 2, y1, 0.0, h))
    y = ymin
    while y <= y1 + 0.5:
        add(*_box_mesh(xl - tick, y - thick / 2, xl + thick / 2, y + thick / 2, 0.0, h + 3))
        y += sy
    return verts, tris


def _guide_mesh(outline: Sequence[tuple[float, float]], half: float = 5.0, z0: float = 14.0, h: float = 6.0):
    pts = [(float(x), float(y)) for x, y in outline if x is not None and y is not None]
    if len(pts) < 2:
        return [], []
    verts: list[tuple[float, float, float]] = []
    tris: list[tuple[int, int, int]] = []
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 1.0:
            continue
        nx, ny = -dy / L, dx / L
        base = len(verts)
        verts += [
            (x0 + nx * half, y0 + ny * half, z0),
            (x0 - nx * half, y0 - ny * half, z0),
            (x1 + nx * half, y1 + ny * half, z0),
            (x1 - nx * half, y1 - ny * half, z0),
            (x0 + nx * half, y0 + ny * half, z0 + h),
            (x0 - nx * half, y0 - ny * half, z0 + h),
            (x1 + nx * half, y1 + ny * half, z0 + h),
            (x1 - nx * half, y1 - ny * half, z0 + h),
        ]
        a = base
        tris += [
            (a, a + 2, a + 3), (a, a + 3, a + 1),
            (a + 4, a + 5, a + 7), (a + 4, a + 7, a + 6),
            (a, a + 1, a + 5), (a, a + 5, a + 4),
            (a + 2, a + 6, a + 7), (a + 2, a + 7, a + 3),
            (a, a + 4, a + 6), (a, a + 6, a + 2),
            (a + 1, a + 3, a + 7), (a + 1, a + 7, a + 5),
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
    tube_z: float = 14.0,
    include_legend: bool = False,
    include_ground: bool = False,
) -> Path:
    del include_legend, include_ground
    out_path = Path(out_path)
    outline = list(outline_points or [])
    codes = [c for c in sequence if get_part(c) is not None]
    parts = [get_part(c) for c in codes]
    built = path_length(parts) if parts else 0.0
    if outline and len(outline) >= 2 and built > 1.0:
        outline = _fit_outline(outline, built)
    if outline and len(outline) >= 2:
        start = Pose(float(outline[0][0]), float(outline[0][1]), _heading_of(outline))
    else:
        start = Pose(0.0, 0.0, 0.0)
    poses = compute_track_path(parts, start=start) if parts else [start]

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
    if outline and len(outline) >= 2:
        ensure(GUIDE_COLOR)
    ensure(RULER_COLOR)
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

    if outline and len(outline) >= 2:
        gv, gt = _guide_mesh(outline, z0=tube_z)
        if gv and gt:
            vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in gv)
            txml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a, b, c in gt)
            pi = ensure(GUIDE_COLOR)
            objects.append(
                f'<object id="{oid}" name="red_guide" type="model" pid="1" pindex="{pi}">'
                f"<mesh><vertices>{vxml}</vertices><triangles>{txml}</triangles></mesh></object>"
            )
            items.append(f'<item objectid="{oid}" />')
            oid += 1

    xs = [float(p.x) for p in poses] + [float(p[0]) for p in outline]
    ys = [float(p.y) for p in poses] + [float(p[1]) for p in outline]
    rv, rt = _ruler_meshes(xs, ys)
    if rv and rt:
        vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in rv)
        txml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a, b, c in rt)
        pi = ensure(RULER_COLOR)
        objects.append(
            f'<object id="{oid}" name="xy_rulers" type="model" pid="1" pindex="{pi}">'
            f"<mesh><vertices>{vxml}</vertices><triangles>{txml}</triangles></mesh></object>"
        )
        items.append(f'<item objectid="{oid}" />')

    bases = "".join(
        f'<base name="mat{i}" displaycolor="#{col}FF" />' for i, col in enumerate(color_list)
    )
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<metadata name="Title">{title}</metadata>'
        '<metadata name="Description">Coloured pieces, red guide, X/Y floor rulers in millimetres</metadata>'
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
