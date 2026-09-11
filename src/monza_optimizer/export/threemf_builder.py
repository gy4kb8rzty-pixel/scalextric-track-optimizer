"""3MF for Microsoft 3D Builder: watertight coloured pieces, red guide, rulers."""

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
RULER_COLOR = "FFFFFF"
NUMBER_COLOR = "1A1A1A"


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


def _tri_area2(verts, a, b, c) -> float:
    ax, ay, az = verts[a]
    bx, by, bz = verts[b]
    cx, cy, cz = verts[c]
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    return nx * nx + ny * ny + nz * nz


def _clean_mesh(verts, tris, min_area2: float = 1e-8):
    n = len(verts)
    out = []
    for a, b, c in tris:
        if a == b or b == c or a == c:
            continue
        if min(a, b, c) < 0 or max(a, b, c) >= n:
            continue
        if _tri_area2(verts, a, b, c) < min_area2:
            continue
        out.append((a, b, c))
    return verts, out


def _box_mesh(x0, y0, x1, y1, z0=0.0, z1=10.0):
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    if z1 < z0:
        z0, z1 = z1, z0
    if (x1 - x0) < 0.5 or (y1 - y0) < 0.5 or (z1 - z0) < 0.5:
        return [], []
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
    return _clean_mesh(verts, tris)


def _dedupe_xy(outline):
    pts = []
    for x, y in outline:
        if x is None or y is None:
            continue
        p = (float(x), float(y))
        if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) >= 1.0:
            pts.append(p)
    return pts


def _guide_mesh(outline, half=5.0, z0=14.0, h=6.0):
    pts = _dedupe_xy(outline)
    if len(pts) < 2:
        return [], []
    headings = []
    for i in range(len(pts)):
        if i < len(pts) - 1:
            dx, dy = pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]
        else:
            dx, dy = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
        headings.append(math.degrees(math.atan2(dy, dx)))
    verts: list[tuple[float, float, float]] = []
    for (x, y), hd in zip(pts, headings):
        verts.extend(_ring(Pose(x, y, hd), half, z0, h))
    tris: list[tuple[int, int, int]] = []
    for i in range(len(pts) - 1):
        a, b = 4 * i, 4 * (i + 1)
        tris += [(a + 2, b + 2, b + 3), (a + 2, b + 3, a + 3)]
        tris += [(a, a + 1, b + 1), (a, b + 1, b)]
        tris += [(a, a + 2, b + 2), (a, b + 2, b)]
        tris += [(a + 1, b + 1, b + 3), (a + 1, b + 3, a + 3)]
    s = 0
    e = 4 * (len(pts) - 1)
    tris += [(s, s + 2, s + 3), (s, s + 3, s + 1)]
    tris += [(e, e + 1, e + 3), (e, e + 3, e + 2)]
    return _clean_mesh(verts, tris)


def _mesh_xml_parts(parts) -> str:
    verts, tris_xml = [], []
    for v, t, pi in parts:
        v, t = _clean_mesh(v, t)
        if not v or not t:
            continue
        off = len(verts)
        verts.extend(v)
        for a, b, c in t:
            tris_xml.append(f'<triangle v1="{a + off}" v2="{b + off}" v3="{c + off}" p1="{pi}" />')
    if not verts or not tris_xml:
        return ""
    vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in verts)
    return f"<mesh><vertices>{vxml}</vertices><triangles>{''.join(tris_xml)}</triangles></mesh>"


def _piece_stations(part, code: str, pose0: Pose, steps: int = 8):
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
    out = []
    hr0 = math.radians(pose0.heading_degrees)
    c, s = math.cos(hr0), math.sin(hr0)
    for lp in local:
        x = pose0.x + lp.x * c - lp.y * s
        y = pose0.y + lp.x * s + lp.y * c
        out.append(Pose(x, y, pose0.heading_degrees + lp.heading_degrees))
    return out


def _tube_from_stations(stations, colors, half_w=78.0, z0=0.0, h=8.0):
    if len(stations) < 2:
        return [], [], []
    verts = []
    for st in stations:
        verts.extend(_ring(st, half_w, z0, h))
    tris = []
    p1 = []
    for i in range(len(stations) - 1):
        a, b = 4 * i, 4 * (i + 1)
        segs = [
            (a + 2, b + 2, b + 3), (a + 2, b + 3, a + 3),
            (a, a + 1, b + 1), (a, b + 1, b),
            (a, a + 2, b + 2), (a, b + 2, b),
            (a + 1, b + 1, b + 3), (a + 1, b + 3, a + 3),
        ]
        col = colors[i] if i < len(colors) else colors[-1]
        tris.extend(segs)
        p1.extend([col] * len(segs))
    s = 0
    e = 4 * (len(stations) - 1)
    cap = [(s, s + 2, s + 3), (s, s + 3, s + 1), (e, e + 1, e + 3), (e, e + 3, e + 2)]
    tris.extend(cap)
    p1.extend([colors[0], colors[0], colors[-1], colors[-1]])
    return verts, tris, p1


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

    def add_parts(name: str, colored):
        nonlocal oid
        packed = []
        default_pi = 0
        for v, t, col in colored:
            pi = ensure(col)
            default_pi = pi
            packed.append((v, t, pi))
        mesh = _mesh_xml_parts(packed)
        if not mesh:
            return
        objects.append(
            f'<object id="{oid}" name="{name}" type="model" pid="1" pindex="{default_pi}">{mesh}</object>'
        )
        items.append(f'<item objectid="{oid}" />')
        oid += 1

    def add_solid(name: str, verts, tris, col: str):
        add_parts(name, [(verts, tris, col)])

    stations = []
    seg_cols = []
    for i, code in enumerate(codes):
        st = _piece_stations(parts[i], code, poses[i])
        col = color_for(code)
        if stations:
            st = st[1:]
        if not st:
            continue
        if stations:
            seg_cols.append(col)
        stations.append(st[0])
        for nxt in st[1:]:
            stations.append(nxt)
            seg_cols.append(col)
    if len(stations) >= 2:
        tv, tt, tp_cols = _tube_from_stations(stations, seg_cols, z0=track_z)
        by = {}
        for tri, col in zip(tt, tp_cols):
            by.setdefault(col, []).append(tri)
        add_parts("track", [(tv, tris, col) for col, tris in by.items()])

    if outline and len(outline) >= 2:
        gv, gt = _guide_mesh(outline, z0=tube_z)
        add_solid("red_guide", gv, gt, GUIDE_COLOR)

    xs = [float(p.x) for p in poses] + [float(p[0]) for p in outline]
    ys = [float(p.y) for p in poses] + [float(p[1]) for p in outline]
    if xs and ys:
        pad = 200.0
        xmin, xmax = min(xs) - pad, max(xs) + pad
        ymin, ymax = min(ys) - pad, max(ys) + pad
        step = 1000.0
        nx = max(1, int(round(max(1.0, xmax - xmin) / step)))
        ny = max(1, int(round(max(1.0, ymax - ymin) / step)))
        bar_h, bar_w, gap = 12.0, 180.0, 160.0
        x_end = xmin + nx * step
        y_end = ymin + ny * step
        y0 = ymin - gap - bar_w
        y1 = ymin - gap
        x0 = xmin - gap - bar_w
        x1 = xmin - gap
        add_solid("ruler_x", *_box_mesh(x0, y0, x_end, y1, 0.0, bar_h), RULER_COLOR)
        add_solid("ruler_y", *_box_mesh(x0, y1, x1, y_end, 0.0, bar_h), RULER_COLOR)

    if not objects:
        add_solid("empty", *_box_mesh(0, 0, 10, 10, 0, 2), "7F8C8D")

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
