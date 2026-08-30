"""Plan-view graphics: filled official pieces, not centreline sticks."""

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


def _bounds_poly(pieces, pad: float = 80.0):
    xs, ys = [], []
    for _, poly in pieces:
        for x, y in poly:
            xs.append(x)
            ys.append(y)
    if not xs:
        return -pad, -pad, pad, pad
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def _rgb(sku: str) -> tuple[int, int, int]:
    hx = PART_COLORS.get(base_id(sku), "7F8C8D")
    return int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)


def render_svg(sequence: Sequence[str], get_part: Callable, title: str = "Layout") -> str:
    pieces, _ = layout_pieces(sequence, get_part)
    minx, miny, maxx, maxy = _bounds_poly(pieces)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    vw, vh = 900.0, max(220.0, 900.0 * h / w)
    scale = vw / w

    def xy(x: float, y: float) -> tuple[float, float]:
        return (x - minx) * scale, vh - (y - miny) * scale

    paths = []
    for sku, poly in pieces:
        pts = " ".join(f"{xy(x, y)[0]:.1f},{xy(x, y)[1]:.1f}" for x, y in poly)
        col = "#" + PART_COLORS.get(base_id(sku), "7F8C8D")
        paths.append(
            f'<polygon points="{pts}" fill="{col}" fill-opacity="0.92" '
            f'stroke="#1f2933" stroke-width="1.2"/>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:.0f} {vh:.0f}" '
        f'width="900" height="{vh:.0f}">'
        f'<rect width="100%" height="100%" fill="#f7f4ee"/>'
        f'<text x="16" y="28" font-size="18" font-family="sans-serif">{title}</text>'
        + "".join(paths)
        + "</svg>"
    )


def render_png(sequence: Sequence[str], get_part: Callable, size: int = 720) -> bytes:
    pieces, _ = layout_pieces(sequence, get_part)
    minx, miny, maxx, maxy = _bounds_poly(pieces)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    canvas = size
    scale = (canvas - 24) / max(w, h)
    img = bytearray([247, 244, 238] * (canvas * canvas))

    def put(ix: int, iy: int, rgb: tuple[int, int, int]):
        if 0 <= ix < canvas and 0 <= iy < canvas:
            o = (iy * canvas + ix) * 3
            img[o : o + 3] = bytes(rgb)

    def pix(x: float, y: float) -> tuple[int, int]:
        return int(12 + (x - minx) * scale), int(canvas - 12 - (y - miny) * scale)

    for sku, poly in pieces:
        col = _rgb(sku)
        pts = [pix(x, y) for x, y in poly]
        _fill_poly(pts, lambda ix, iy: put(ix, iy, col))
        for i, (x0, y0) in enumerate(pts):
            x1, y1 = pts[(i + 1) % len(pts)]
            _line(x0, y0, x1, y1, lambda ix, iy: put(ix, iy, (30, 30, 30)))
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


def render_pdf(sequence: Sequence[str], get_part: Callable, title: str, lay_text: str) -> bytes:
    pieces, _ = layout_pieces(sequence, get_part)
    minx, miny, maxx, maxy = _bounds_poly(pieces)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    pw, ph = 595.0, 842.0
    box_x, box_y, box_w, box_h = 36.0, 420.0, 523.0, 380.0
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
    y = 400.0
    ops.append("0 0 0 rg")
    for line in lay_text.splitlines()[:28]:
        ops.append(f"BT /F1 8 Tf 36 {y:.1f} Td ({_pdf_esc(line[:90])}) Tj ET")
        y -= 11
        if y < 40:
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
