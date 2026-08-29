"""Plan-view graphics: SVG always; PNG and PDF without extra packages."""

from __future__ import annotations

import io
import struct
import zlib
from typing import Callable, Sequence

from monza_optimizer.catalog.parts import base_id
from monza_optimizer.export.threemf_builder import PART_COLORS
from monza_optimizer.geometry.path import compute_track_path
from monza_optimizer.geometry.pose import Pose


def _poses(sequence: Sequence[str], get_part: Callable) -> list[Pose]:
    parts = [get_part(c) for c in sequence]
    parts = [p for p in parts if p is not None]
    if not parts:
        return [Pose(0, 0, 0)]
    return compute_track_path(parts, start=Pose(0, 0, 0))


def _bounds(poses: list[Pose], pad: float = 120.0):
    xs = [p.x for p in poses]
    ys = [p.y for p in poses]
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def _color(sku: str) -> str:
    return "#" + PART_COLORS.get(base_id(sku), "7F8C8D")


def render_svg(sequence: Sequence[str], get_part: Callable, title: str = "Layout") -> str:
    poses = _poses(sequence, get_part)
    minx, miny, maxx, maxy = _bounds(poses)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    vw, vh = 900.0, 900.0 * h / w
    scale = vw / w

    def xy(p: Pose) -> tuple[float, float]:
        return (p.x - minx) * scale, vh - (p.y - miny) * scale

    segs = []
    for i, sku in enumerate(sequence):
        if i + 1 >= len(poses):
            break
        x0, y0 = xy(poses[i])
        x1, y1 = xy(poses[i + 1])
        segs.append(
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
            f'stroke="{_color(sku)}" stroke-width="10" stroke-linecap="round"/>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:.0f} {vh:.0f}" '
        f'width="900" height="{vh:.0f}">'
        f'<rect width="100%" height="100%" fill="#f7f4ee"/>'
        f'<text x="16" y="28" font-size="18" font-family="sans-serif">{title}</text>'
        + "".join(segs)
        + "</svg>"
    )


def render_png(sequence: Sequence[str], get_part: Callable, size: int = 720) -> bytes:
    poses = _poses(sequence, get_part)
    minx, miny, maxx, maxy = _bounds(poses)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    canvas = size
    scale = (canvas - 16) / max(w, h)
    img = bytearray([247, 244, 238] * (canvas * canvas))

    def put(ix: int, iy: int, rgb: tuple[int, int, int]):
        if 0 <= ix < canvas and 0 <= iy < canvas:
            o = (iy * canvas + ix) * 3
            img[o : o + 3] = bytes(rgb)

    def rgb_of(sku: str) -> tuple[int, int, int]:
        hx = PART_COLORS.get(base_id(sku), "7F8C8D")
        return int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)

    def pix(p: Pose) -> tuple[int, int]:
        x = int(8 + (p.x - minx) * scale)
        y = int(canvas - 8 - (p.y - miny) * scale)
        return x, y

    for i, sku in enumerate(sequence):
        if i + 1 >= len(poses):
            break
        x0, y0 = pix(poses[i])
        x1, y1 = pix(poses[i + 1])
        col = rgb_of(sku)
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            t = s / steps
            ix = int(x0 + (x1 - x0) * t)
            iy = int(y0 + (y1 - y0) * t)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    put(ix + dx, iy + dy, col)
    return _png_rgb(canvas, canvas, bytes(img))


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
    poses = _poses(sequence, get_part)
    minx, miny, maxx, maxy = _bounds(poses)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    pw, ph = 595.0, 842.0
    box_x, box_y, box_w, box_h = 36.0, 420.0, 523.0, 380.0
    scale = min(box_w / w, box_h / h)

    def xy(p: Pose) -> tuple[float, float]:
        return box_x + (p.x - minx) * scale, box_y + (p.y - miny) * scale

    ops = ["0.97 0.96 0.93 rg", f"0 0 {pw:.0f} {ph:.0f} re f", "0 0 0 rg"]
    safe_title = title.replace("(", "[").replace(")", "]")[:80]
    ops.append("BT /F1 14 Tf 36 812 Td (" + _pdf_esc(safe_title) + ") Tj ET")
    for i, sku in enumerate(sequence):
        if i + 1 >= len(poses):
            break
        hx = PART_COLORS.get(base_id(sku), "7F8C8D")
        r, g, b = int(hx[0:2], 16) / 255, int(hx[2:4], 16) / 255, int(hx[4:6], 16) / 255
        x0, y0 = xy(poses[i])
        x1, y1 = xy(poses[i + 1])
        ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG 3 w {x0:.1f} {y0:.1f} m {x1:.1f} {y1:.1f} l S")
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
