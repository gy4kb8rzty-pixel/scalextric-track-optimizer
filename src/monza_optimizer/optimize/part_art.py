"""Map official SKUs to repo-root BMP silhouettes and optional PNG."""

from __future__ import annotations

import re
import struct
import zlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SKU_BMP = {
    "C8205": "c8205.bmp",
    "C8207": "c8207p.bmp",
    "C8200": "c8200p.bmp",
    "C8236": "c8236p.bmp",
    "C8206": "512x512_C8206.bmp",
    "C8206L": "512x512_C8206.bmp",
    "C8206R": "c8206r.bmp",
    "C8234": "c8234p.bmp",
    "C8234L": "c8234lp.bmp",
    "C8234R": "c8234rp.bmp",
    "C8204L": "c8204lp.bmp",
    "C8204R": "c8204rp.bmp",
    "C8235L": "c8235lp.bmp",
    "C8235R": "c8235rp.bmp",
    "C156L": "c156lp.bmp",
    "C156R": "c156rp.bmp",
    "C8010L": "c8010lp.bmp",
    "C8010R": "c8010r.bmp",
    "C8201L": "c8201lp.bmp",
    "C8201R": "c8201rp.bmp",
    "C8202L": "c8202lp.bmp",
    "C8202R": "c8202rp.bmp",
    "C8203": "c8203lp.bmp",
    "C8210": "c8210p.bmp",
    "C8006": "c8006p.bmp",
    "C8295": "c8295p.bmp",
    "C8005": "c8005p.bmp",
    "C8009": "c8009p.bmp",
    "C8031A": "c8031p.bmp",
    "C8031B": "c8031p.bmp",
    "C8246A": "c8246ap.bmp",
    "C8246B": "c8246bp.bmp",
    "C7000": "c7000p.bmp",
    "C7004": "c7036p.bmp",
    "C7007": "c7007lp.bmp",
    "C7010": "c7010rp.bmp",
    "C187L": "c191p.bmp",
    "C187R": "c191p.bmp",
}

_SAFE = re.compile(r"^[A-Za-z0-9_.-]+\.(bmp|png)$", re.I)


def resolve_art_path(filename: str) -> Path | None:
    name = filename.strip()
    if not _SAFE.match(name):
        return None
    if name.lower().endswith(".png"):
        name = name[:-4] + ".bmp"
    direct = REPO_ROOT / name
    if direct.is_file():
        return direct
    key = name.lower()
    for child in REPO_ROOT.iterdir():
        if child.is_file() and child.name.lower() == key:
            return child
    return None


def bmp_to_png(data: bytes) -> bytes:
    if data[:2] != b"BM":
        raise ValueError("not a BMP")
    off = struct.unpack_from("<I", data, 10)[0]
    header = struct.unpack_from("<IiiHHI", data, 14)
    width, height = header[1], header[2]
    bits = header[4]
    if bits != 24:
        raise ValueError("only 24-bit BMP")
    row_raw = ((width * 3 + 3) // 4) * 4
    flip = height > 0
    height = abs(height)
    rows = []
    for y in range(height):
        src_y = height - 1 - y if flip else y
        start = off + src_y * row_raw
        row = bytearray(data[start : start + width * 3])
        for i in range(0, len(row), 3):
            row[i], row[i + 2] = row[i + 2], row[i]
        rows.append(b"\x00" + bytes(row))
    raw = b"".join(rows)
    comp = zlib.compress(raw, 9)

    def chunk(tag: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")


def urls_for_sku(sku: str) -> dict[str, str | None]:
    bmp = SKU_BMP.get(sku)
    if not bmp:
        return {"thumb_bmp": None, "thumb_url": None, "thumb_png": None}
    stem = bmp[:-4] if bmp.lower().endswith(".bmp") else bmp
    return {
        "thumb_bmp": bmp,
        "thumb_url": f"/part-art/{bmp}",
        "thumb_png": f"/part-art/{stem}.png",
    }
