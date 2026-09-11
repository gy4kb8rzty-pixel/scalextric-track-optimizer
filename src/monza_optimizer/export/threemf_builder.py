"""3MF for 3D Builder: one welded track tube + red guide."""

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


def _heading_of(outline: Sequence[tuple[float, float]]) -> float:
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


def _ring(pose: Pose, half_w: float, z0: float, h: float):
    hr = math.radians(pose.heading_degrees)
    nx, ny = -math.sin(hr), math.cos(hr)
    return [
        (pose.x + nx * half_w, pose.y + ny * half_w, z0),
        (pose.x - nx * half_w, pose.y - ny * half_w, z0),
        (pose.x + nx * half_w, pose.y + ny * half_w, z0 + h),
        (pose.x - nx * half_w, pose.y - ny * half_w, z0 + h),
    ]


def _repair_mesh(verts, labeled):
    """Weld coincident verts and drop degenerate triangles. labeled: (a,b,c,pi)."""
    key_map = {}
    remap = []
    out_v = []
    for x, y, z in verts:
        key = (round(x, 2), round(y, 2), round(z, 2))
        if key not in key_map:
            key_map[key] = len(out_v)
            out_v.append((float(x), float(y), float(z)))
        remap.append(key_map[key])
    out_t = []
    for a, b, c, pi in labeled:
        a, b, c = remap[a], remap[b], remap[c]
        if a == b or b == c or a == c:
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
        out_t.append((a, b, c, pi))
    return out_v, out_t


def _mesh_xml(verts, labeled) -> str:
    verts, labeled = _repair_mesh(verts, labeled)
    if not verts or not labeled:
        return ""
    vxml = "".join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x, y, z in verts)
    txml = "".join(
        f'<triangle v1="{a}" v2="{b}" v3="{c}" p1="{pi}" />' for a, b, c, pi in labeled
    )
    return f"<mesh><vertices>{vxml}</vertices><triangles>{txml}</triangles></mesh>"


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
    verts = []
    for (x, y), hd in zip(pts, headings):
        verts.extend(_ring(Pose(x, y, hd), half, z0, h))
    labeled = []
    for i in range(len(pts) - 1):
        a, b = 4 * i, 4 * (i + 1)
        labeled += [
            (a + 2, b + 2, b + 3, 0), (a + 2, b + 3, a + 3, 0),
            (a, a + 1, b + 1, 0), (a, b + 1, b, 0),
            (a, a + 2, b + 2, 0), (a, b + 2, b, 0),
            (a + 1, b + 1, b + 3, 0), (a + 1, b + 3, a + 3, 0),
        ]
    s = 0
    e = 4 * (len(pts) - 1)
    labeled += [(s, s + 2, s + 3, 0), (s, s + 3, s + 1, 0), (e, e + 1, e + 3, 0), (e, e + 3, e + 2, 0)]
    return verts, labeled


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
    hr0 = math.radians(pose0.heading_degrees)
    c, s = math.cos(hr0), math.sin(hr0)
    out = []
    for lp in local:
        x = pose0.x + lp.x * c - lp.y * s
        y = pose0.y + lp.x * s + lp.y * c
        out.append(Pose(x, y, pose0.heading_degrees + lp.heading_degrees))
    return out


def _tube_from_stations(stations, color_ids, half_w=78.0, z0=0.0, h=8.0):
    if len(stations) < 2:
        return [], []
    verts = []
    for st in stations:
        verts.extend(_ring(st, half_w, z0, h))
    labeled = []
    for i in range(len(stations) - 1):
        a, b = 4 * i, 4 * (i + 1)
        pi = color_ids[i] if i < len(color_ids) else color_ids[-1]
        labeled += [
            (a + 2, b + 2, b + 3, pi), (a + 2, b + 3, a + 3, pi),
            (a, a + 1, b + 1, pi), (a, b + 1, b, pi),
            (a, a + 2, b + 2, pi), (a, b + 2, b, pi),
            (a + 1, b + 1, b + 3, pi), (a + 1, b + 3, a + 3, pi),
        ]
    s = 0
    e = 4 * (len(stations) - 1)
    labeled += [
        (s, s + 2, s + 3, color_ids[0]), (s, s + 3, s + 1, color_ids[0]),
        (e, e + 1, e + 3, color_ids[-1]), (e, e + 3, e + 2, color_ids[-1]),
    ]
    return verts, labeled


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
    if not color_list:
        ensure("7F8C8D")

    objects: list[str] = []
    items: list[str] = []
    oid = 2

    def add_object(name: str, verts, labeled, default_pi: int):
        nonlocal oid
        mesh = _mesh_xml(verts, labeled)
        if not mesh:
            return
        objects.append(
            f'<object id="{oid}" name="{name}" type="model" pid="1" pindex="{default_pi}">{mesh}</object>'
        )
        items.append(f'<item objectid="{oid}" />')
        oid += 1

    stations = []
    seg_ids = []
    for i, code in enumerate(codes):
        st = _piece_stations(parts[i], code, poses[i])
        pi = ensure(color_for(code))
        if stations:
            st = st[1:]
        if not st:
            continue
        if stations:
            seg_ids.append(pi)
        stations.append(st[0])
        for nxt in st[1:]:
            stations.append(nxt)
            seg_ids.append(pi)
    if len(stations) >= 2 and seg_ids:
        tv, labeled = _tube_from_stations(stations, seg_ids, z0=track_z)
        add_object("track", tv, labeled, seg_ids[0])

    if outline and len(outline) >= 2:
        gv, gl = _guide_mesh(outline, z0=tube_z)
        gpi = ensure(GUIDE_COLOR)
        gl = [(a, b, c, gpi) for a, b, c, _ in gl]
        add_object("red_guide", gv, gl, gpi)

    if not objects:
        add_object("empty", [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0), (0, 0, 2), (10, 0, 2), (10, 10, 2), (0, 10, 2)],
                   [(0, 1, 2, 0), (0, 2, 3, 0), (4, 6, 5, 0), (4, 7, 6, 0),
                    (0, 4, 5, 0), (0, 5, 1, 0), (1, 5, 6, 0), (1, 6, 2, 0),
                    (2, 6, 7, 0), (2, 7, 3, 0), (3, 7, 4, 0), (3, 4, 0, 0)], 0)

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
