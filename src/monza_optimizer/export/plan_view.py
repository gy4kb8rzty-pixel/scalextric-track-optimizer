"""Plan-view graphics: filled pieces, colour key, red official centreline."""

from __future__ import annotations

import io
import math
import struct
import zlib
from typing import Callable, Sequence

from monza_optimizer.catalog.geometry_types import CurveGeometry, StraightGeometry
from monza_optimizer.catalog.parts import base_id
from monza_optimizer.export.threemf_builder import PART_COLORS
from monza_optimizer.geometry.path import compute_track_path
from monza_optimizer.geometry.pose import Pose

HALF_W = 78.0
RED = (192, 57, 43)

COLOR_KEY = [
    ("C8205", "Straight"),
    ("C8207", "Half"),
    ("C8200", "Quarter"),
    ("C8236", "Short"),
    ("C8206", "R2 45"),
    ("C8234", "R2 22.5"),
    ("C8204", "R3"),
    ("C8235", "R4"),
    ("C8201", "R1 hairpin"),
    ("C187", "Banked"),
    ("C8010", "Chicane"),
]


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


def _offset(pose: Pose, half: float) -> tuple[float, float]:
    hr = math.radians(pose.heading_degrees)
    nx, ny = -math.sin(hr), math.cos(hr)
    return pose.x + nx * half, pose.y + ny * half


def _step_curve(pose: Pose, radius: float, dt: float) -> Pose:
    hr = math.radians(pose.heading_degrees)
    ar = math.radians(dt)
    td = 1.0 if dt >= 0 else -1.0
    lx = radius * math.sin(abs(ar))
    ly = td * radius * (1.0 - math.cos(abs(ar)))
    wx = lx * math.cos(hr) - ly * math.sin(hr)
    wy = lx * math.sin(hr) + ly * math.cos(hr)
    return Pose(pose.x + wx, pose.y + wy, pose.heading_degrees + dt)


def piece_polygon(part, code: str, start: Pose, steps: int = 8) -> list[tuple[float, float]]:
    g = part.geometry
    if isinstance(g, StraightGeometry):
        hr = math.radians(start.heading_degrees)
        end = Pose(start.x + g.length * math.cos(hr), start.y + g.length * math.sin(hr), start.heading_degrees)
        return [
            _offset(start, HALF_W),
            _offset(end, HALF_W),
            _offset(end, -HALF_W),
            _offset(start, -HALF_W),
        ]
    if not isinstance(g, CurveGeometry):
        return [_offset(start, HALF_W), _offset(start, -HALF_W)]
    n = max(4, steps)
    dt = _signed_angle(part, code) / n
    pose = start
    outer = [_offset(pose, HALF_W)]
    inner = [_offset(pose, -HALF_W)]
    for _ in range(n):
        pose = _step_curve(pose, g.radius, dt)
        outer.append(_offset(pose, HALF_W))
        inner.append(_offset(pose, -HALF_W))
    inner.reverse()
    return outer + inner


def layout_pieces(sequence: Sequence[str], get_part: Callable):
    codes = [c for c in sequence if get_part(c) is not None]
    parts = [get_part(c) for c in codes]
    poses = compute_track_path(parts, start=Pose(0.0, 0.0, 0.0)) if parts else [Pose(0, 0, 0)]
    pieces = [(code, piece_polygon(parts[i], code, poses[i])) for i, code in enumerate(codes)]
    return pieces, poses


def keys_used(sequence: Sequence[str]) -> list[tuple[str, str]]:
    used = {base_id(c) for c in sequence}
    return [(sku, label) for sku, label in COLOR_KEY if sku in used]


def _bounds(pieces, outline, pad: float = 80.0):
    xs, ys = [], []
    for _, poly in pieces:
        for x, y in poly:
            xs.append(x)
            ys.append(y)
    for x, y in outline or []:
        xs.append(x)
        ys.append(y)
    if not xs:
        return -pad, -pad, pad, pad
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def _rgb(sku: str) -> tuple[int, int, int]:
    hx = PART_COLORS.get(base_id(sku), "7F8C8D")
    return int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)


def render_svg(
    sequence: Sequence[str],
    get_part: Callable,
    title: str = "Layout",
    outline_points: Sequence[tuple[float, float]] | None = None,
) -> str:
    pieces, _ = layout_pieces(sequence, get_part)
    outline = list(outline_points or [])
    minx, miny, maxx, maxy = _bounds(pieces, outline)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    vw, vh = 900.0, max(260.0, 900.0 * h / w + 36)
    scale = vw / w

    def xy(x: float, y: float) -> tuple[float, float]:
        return (x - minx) * scale, vh - 40 - (y - miny) * scale

    paths = []
    for sku, poly in pieces:
        pts = " ".join(f"{xy(x, y)[0]:.1f},{xy(x, y)[1]:.1f}" for x, y in poly)
        col = "#" + PART_COLORS.get(base_id(sku), "7F8C8D")
        paths.append(
            f'<polygon points="{pts}" fill="{col}" fill-opacity="0.88" '
            f'stroke="#1f2933" stroke-width="1.1"/>'
        )
    if len(outline) >= 2:
        d = " ".join(f"{xy(x, y)[0]:.1f},{xy(x, y)[1]:.1f}" for x, y in outline)
        paths.append(
            f'<polyline points="{d}" fill="none" stroke="#c0392b" '
            f'stroke-width="2.4" stroke-linejoin="round"/>'
        )
    legend = []
    x = 16.0
    legend.append(
        f'<line x1="{x}" y1="{vh-21}" x2="{x+18}" y2="{vh-21}" stroke="#c0392b" stroke-width="3"/>'
    )
    legend.append(
        f'<text x="{x+22}" y="{vh-16}" font-size="12" font-family="sans-serif">Target circuit</text>'
    )
    x += 130
    for sku, label in keys_used(sequence):
        col = "#" + PART_COLORS.get(sku, "7F8C8D")
        legend.append(f'<rect x="{x:.0f}" y="{vh-28:.0f}" width="14" height="14" fill="{col}" stroke="#222"/>')
        legend.append(
            f'<text x="{x+18:.0f}" y="{vh-16:.0f}" font-size="12" font-family="sans-serif">{label}</text>'
        )
        x += 18 + 7 * len(label) + 16
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:.0f} {vh:.0f}" '
        f'width="900" height="{vh:.0f}">'
        f'<rect width="100%" height="100%" fill="#f7f4ee"/>'
        f'<text x="16" y="22" font-size="16" font-family="sans-serif">{title}</text>'
        + "".join(paths)
        + "".join(legend)
        + "</svg>"
    )


def render_png(
    sequence: Sequence[str],
    get_part: Callable,
    size: int = 720,
    outline_points: Sequence[tuple[float, float]] | None = None,
) -> bytes:
    pieces, _ = layout_pieces(sequence, get_part)
    outline = list(outline_points or [])
    minx, miny, maxx, maxy = _bounds(pieces, outline)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    canvas = size
    top, bot = 28, 36
    scale = (canvas - 24 - top - bot) / max(w, h)
    img = bytearray([247, 244, 238] * (canvas * canvas))

    def put(ix: int, iy: int, rgb: tuple[int, int, int]):
        if 0 <= ix < canvas and 0 <= iy < canvas:
            o = (iy * canvas + ix) * 3
            img[o : o + 3] = bytes(rgb)

    def pix(x: float, y: float) -> tuple[int, int]:
        return int(12 + (x - minx) * scale), int(canvas - bot - 8 - (y - miny) * scale)

    for sku, poly in pieces:
        col = _rgb(sku)
        pts = [pix(x, y) for x, y in poly]
        _fill_poly(pts, lambda ix, iy: put(ix, iy, col))
        for i, (x0, y0) in enumerate(pts):
            x1, y1 = pts[(i + 1) % len(pts)]
            _line(x0, y0, x1, y1, lambda ix, iy: put(ix, iy, (30, 30, 30)))
    if len(outline) >= 2:
        opts = [pix(x, y) for x, y in outline]
        for i in range(len(opts) - 1):
            _line(opts[i][0], opts[i][1], opts[i + 1][0], opts[i + 1][1], lambda ix, iy: put(ix, iy, RED))
            _line(opts[i][0], opts[i][1] + 1, opts[i + 1][0], opts[i + 1][1] + 1, lambda ix, iy: put(ix, iy, RED))
    lx = 8
    ly = canvas - 22
    for dx in range(16):
        put(lx + dx, ly + 6, RED)
    lx = 8
    for sku, _label in keys_used(sequence):
        col = _rgb(sku)
        for dx in range(12):
            for dy in range(12):
                put(lx + dx, ly + dy, col)
        lx += 18
    return _png_rgb(canvas, canvas, bytes(img))


def _line(x0, y0, x1, y1, plot):
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for s in range(steps + 1):
        t = s / steps
        plot(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t))


def _fill_poly(pts, plot):
    if len(pts) < 3:
        return
    ys = [p[1] for p in pts]
    for y in range(min(ys), max(ys) + 1):
        xs = []
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if y0 == y1:
                continue
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(int(x0 + t * (x1 - x0)))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(xs[i], xs[i + 1] + 1):
                plot(x, y)


def _png_rgb(width: int, height: int, raw: bytes) -> bytes:
    rows = b""
    row_bytes = width * 3
    for y in range(height):
        rows += b"\x00" + raw[y * row_bytes : (y + 1) * row_bytes]
    comp = zlib.compress(rows, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")


def render_pdf(
    sequence: Sequence[str],
    get_part: Callable,
    title: str,
    lay_text: str,
    outline_points: Sequence[tuple[float, float]] | None = None,
) -> bytes:
    del lay_text
    pieces, _ = layout_pieces(sequence, get_part)
    outline = list(outline_points or [])
    minx, miny, maxx, maxy = _bounds(pieces, outline)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    pw, ph = 595.0, 842.0
    box_x, box_y, box_w, box_h = 36.0, 80.0, 523.0, 680.0
    scale = min(box_w / w, box_h / h)

    def xy(x: float, y: float) -> tuple[float, float]:
        return box_x + (x - minx) * scale, box_y + (y - miny) * scale

    ops = ["0.97 0.96 0.93 rg", f"0 0 {pw:.0f} {ph:.0f} re f"]
    safe_title = title.replace("(", "[").replace(")", "]")[:80]
    ops.append("0 0 0 rg")
    ops.append("BT /F1 14 Tf 36 812 Td (" + _pdf_esc(safe_title) + ") Tj ET")
    for sku, poly in pieces:
        r, g, b = [c / 255 for c in _rgb(sku)]
        ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg 0.12 0.12 0.14 RG 0.6 w")
        x0, y0 = xy(*poly[0])
        ops.append(f"{x0:.1f} {y0:.1f} m")
        for x, y in poly[1:]:
            xx, yy = xy(x, y)
            ops.append(f"{xx:.1f} {yy:.1f} l")
        ops.append("h B")
    if len(outline) >= 2:
        ops.append("0.75 0.22 0.17 RG 1.6 w")
        x0, y0 = xy(*outline[0])
        ops.append(f"{x0:.1f} {y0:.1f} m")
        for x, y in outline[1:]:
            xx, yy = xy(x, y)
            ops.append(f"{xx:.1f} {yy:.1f} l")
        ops.append("S")
    ops.append("0 0 0 rg")
    ops.append("BT /F1 10 Tf 36 56 Td (Red = target circuit. Colour key = parts.) Tj ET")
    x = 36.0
    ops.append("0.75 0.22 0.17 RG 2 w")
    ops.append(f"{x:.1f} 41 m {x+16:.1f} 41 l S")
    ops.append("0 0 0 rg")
    ops.append(f"BT /F1 8 Tf {x+20:.1f} 38 Td (Target) Tj ET")
    x += 70
    for sku, label in keys_used(sequence):
        r, g, b = [c / 255 for c in _rgb(sku)]
        ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.1f} 36 10 10 re f")
        ops.append("0 0 0 rg")
        ops.append(f"BT /F1 8 Tf {x+14:.1f} 38 Td ({_pdf_esc(label)}) Tj ET")
        x += 14 + 6 * len(label) + 10
        if x > 520:
            break
    stream = "\n".join(ops).encode("latin-1", "replace")
    objs = []
    objs.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objs.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objs.append(
        (
            f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {pw:.0f} {ph:.0f}] "
            f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        ).encode()
    )
    objs.append(b"4 0 obj << /Length " + str(len(stream)).encode() + b" >> stream\n" + stream + b"\nendstream endobj\n")
    objs.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(out.tell())
        out.write(obj)
    xref = out.tell()
    out.write(f"xref\n0 {len(objs)+1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def _pdf_esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
