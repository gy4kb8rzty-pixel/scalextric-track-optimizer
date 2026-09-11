"""3MF: part colours via one object per colour (object-level material, no triangle p1)."""

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


def _heading_of(outline):
    if not outline or len(outline) < 2:
        return 0.0
    return math.degrees(math.atan2(outline[1][1] - outline[0][1], outline[1][0] - outline[0][0]))


def _poly_len(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def _fit_outline(outline, built_mm):
    pts = [(float(x), float(y)) for x, y in outline]
    if len(pts) < 2 or built_mm < 1.0:
        return pts
    L = _poly_len(pts)
    if L < 1.0:
        return pts
    s = built_mm / L
    x0, y0 = pts[0]
    return [((x - x0) * s + x0, (y - y0) * s + y0) for x, y in pts]


def _ring(x, y, heading_deg, half_w, z0, h):
    hr = math.radians(heading_deg)
    nx, ny = -math.sin(hr), math.cos(hr)
    return [
        (x + nx * half_w, y + ny * half_w, z0),
        (x - nx * half_w, y - ny * half_w, z0),
        (x + nx * half_w, y + ny * half_w, z0 + h),
        (x - nx * half_w, y - ny * half_w, z0 + h),
    ]


def _weld(verts, tris):
    key_map, remap, out_v = {}, [], []
    for x, y, z in verts:
        key = (round(x, 2), round(y, 2), round(z, 2))
        if key not in key_map:
            key_map[key] = len(out_v)
            out_v.append((float(x), float(y), float(z)))
        remap.append(key_map[key])
    out_t = []
    for a, b, c in tris:
        a, b, c = remap[a], remap[b], remap[c]
        if len({a, b, c}) < 3:
            continue
        ax, ay, az = out_v[a]
        bx, by, bz = out_v[b]
        cx, cy, cz = out_v[c]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        if nx * nx + ny * ny + nz * nz < 1e-8:
            continue
        out_t.append((a, b, c))
    return out_v, out_t


def _segment_box(p0, p1, half_w, z0, h):
    x0, y0, h0 = p0
    x1, y1, h1 = p1
    v0 = _ring(x0, y0, h0, half_w, z0, h)
    v1 = _ring(x1, y1, h1, half_w, z0, h)
    verts = v0 + v1
    tris = [
        (2, 6, 7), (2, 7, 3),
        (0, 1, 5), (0, 5, 4),
        (0, 2, 6), (0, 6, 4),
        (1, 5, 7), (1, 7, 3),
        (0, 2, 3), (0, 3, 1),
        (4, 5, 7), (4, 7, 6),
    ]
    return _weld(verts, tris)


def _piece_stations(part, code, pose0, steps=8):
    if isinstance(part.geometry, CurveGeometry) and abs(_signed_angle(part, code)) >= 0.5:
        ang = _signed_angle(part, code)
        R = float(part.geometry.radius)
        n = max(4, steps)
        local = [Pose(0, 0, 0)]
        pose = Pose(0, 0, 0)
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
            local.append(pose)
    else:
        L = max(1.0, float(getattr(part.geometry, "length", 350.0)))
        local = [Pose(0, 0, 0), Pose(L, 0, 0)]
    hr0 = math.radians(pose0.heading_degrees)
    c, s = math.cos(hr0), math.sin(hr0)
    out = []
    for lp in local:
        x = pose0.x + lp.x * c - lp.y * s
        y = pose0.y + lp.x * s + lp.y * c
        out.append((x, y, pose0.heading_degrees + lp.heading_degrees))
    return out


def _dedupe_xy(outline):
    pts = []
    for x, y in outline:
        if x is None or y is None:
            continue
        p = (float(x), float(y))
        if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) >= 1.0:
            pts.append(p)
    return pts


def _mesh_xml(verts, tris) -> str:
    verts, tris = _weld(verts, tris)
    if not verts or not tris:
        return ""
    vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in verts)
    txml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a, b, c in tris)
    return f"<mesh><vertices>{vxml}</vertices><triangles>{txml}</triangles></mesh>"


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

    buckets: dict[str, tuple[list, list]] = {}

    def add_to(col: str, v, t):
        ensure(col)
        if col not in buckets:
            buckets[col] = ([], [])
        bv, bt = buckets[col]
        off = len(bv)
        bv.extend(v)
        bt.extend((a + off, b + off, c + off) for a, b, c in t)

    stations = []
    colors = []
    for i, code in enumerate(codes):
        st = _piece_stations(parts[i], code, poses[i])
        col = color_for(code)
        if stations:
            st = st[1:]
        if not st:
            continue
        if stations:
            colors.append(col)
        stations.append(st[0])
        for nxt in st[1:]:
            stations.append(nxt)
            colors.append(col)
    for i in range(len(stations) - 1):
        v, t = _segment_box(stations[i], stations[i + 1], 78.0, track_z, 8.0)
        add_to(colors[i] if i < len(colors) else "7F8C8D", v, t)

    pts = _dedupe_xy(outline)
    if len(pts) >= 2:
        g = []
        for i, (x, y) in enumerate(pts):
            if i < len(pts) - 1:
                dx, dy = pts[i + 1][0] - x, pts[i + 1][1] - y
            else:
                dx, dy = x - pts[i - 1][0], y - pts[i - 1][1]
            g.append((x, y, math.degrees(math.atan2(dy, dx))))
        for i in range(len(g) - 1):
            v, t = _segment_box(g[i], g[i + 1], 5.0, tube_z, 6.0)
            add_to(GUIDE_COLOR, v, t)

    objects, items = [], []
    oid = 2
    for col, (v, t) in buckets.items():
        mesh = _mesh_xml(v, t)
        if not mesh:
            continue
        pi = ensure(col)
        objects.append(
            f'<object id="{oid}" name="part_{col}" type="model" pid="1" pindex="{pi}">{mesh}</object>'
        )
        items.append(f'<item objectid="{oid}" />')
        oid += 1
    if not objects:
        objects.append(
            '<object id="2" name="empty" type="model"><mesh>'
            '<vertices><vertex x="0" y="0" z="0" /><vertex x="10" y="0" z="0" />'
            '<vertex x="10" y="10" z="0" /></vertices>'
            '<triangles><triangle v1="0" v2="1" v3="2" /></triangles></mesh></object>'
        )
        items.append('<item objectid="2" />')
        ensure("7F8C8D")

    safe_title = title.replace("&", "&").replace("<", "<").replace(">", ">")
    bases = "".join(
        f'<base name="mat{i}" displaycolor="#{col}FF" />' for i, col in enumerate(color_list)
    )
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<metadata name="Title">{safe_title}</metadata>'
        '<metadata name="Application">Track Optimizer</metadata>'
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
