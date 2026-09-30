"""Plan-view graphics: filled pieces, colour key, red official centreline, XY rulers."""
from __future__ import annotations
import io, math, struct, zlib
from typing import Callable, Sequence
from monza_optimizer.catalog.geometry_types import CurveGeometry, StraightGeometry
from monza_optimizer.catalog.parts import base_id
from monza_optimizer.export.threemf_builder import PART_COLORS
from monza_optimizer.geometry.path import compute_track_path
from monza_optimizer.geometry.pose import Pose

HALF_W = 78.0
RED = (192, 57, 43)
INK = (20, 20, 20)
COLOR_KEY = [("C8205","STR"),("C8207","HALF"),("C8200","QTR"),("C8236","SHORT"),("C8206","R2"),("C8234","R2.22"),("C8204","R3"),("C8235","R4"),("C8201","R1"),("C187","BANK"),("C8010","CHIC")]
_GLYPH = {" ":[0,0,0,0,0,0,0],".":[0,0,0,0,0,0,2],"-":[0,0,0,31,0,0,0],"0":[14,17,19,21,25,17,14],"1":[4,12,4,4,4,4,14],"2":[14,17,1,2,4,8,31],"3":[14,17,1,6,1,17,14],"4":[2,6,10,18,31,2,2],"5":[31,16,30,1,1,17,14],"6":[14,16,16,30,17,17,14],"7":[31,1,2,4,8,8,8],"8":[14,17,17,14,17,17,14],"9":[14,17,17,15,1,1,14],"A":[14,17,17,31,17,17,17],"B":[30,17,17,30,17,17,30],"C":[14,17,16,16,16,17,14],"D":[30,17,17,17,17,17,30],"E":[31,16,16,30,16,16,31],"F":[31,16,16,30,16,16,16],"G":[14,17,16,19,17,17,14],"H":[17,17,17,31,17,17,17],"I":[14,4,4,4,4,4,14],"K":[17,18,20,24,20,18,17],"L":[16,16,16,16,16,16,31],"M":[17,27,21,21,17,17,17],"N":[17,25,21,19,17,17,17],"O":[14,17,17,17,17,17,14],"P":[30,17,17,30,16,16,16],"Q":[14,17,17,17,21,18,13],"R":[30,17,17,30,20,18,17],"S":[14,17,16,14,1,17,14],"T":[31,4,4,4,4,4,4],"U":[17,17,17,17,17,17,14],"X":[17,10,4,4,4,10,17],"Y":[17,17,10,4,4,4,4]}

def _tick_step(span):
    span = max(float(span), 1.0)
    if span >= 8000: return 2000.0
    if span >= 3500: return 1000.0
    return 500.0

def _space_label(w, h):
    return f"{w/1000.0:.1f} M X {h/1000.0:.1f} M"

def _blit_text(put, x, y, text, rgb=INK, scale=2):
    cx = x
    for ch in text.upper():
        rows = _GLYPH.get(ch, _GLYPH[" "])
        for ry, bits in enumerate(rows):
            for rx in range(5):
                if bits & (16 >> rx):
                    for dy in range(scale):
                        for dx in range(scale):
                            put(cx + rx*scale + dx, y + ry*scale + dy, rgb)
        cx += 6*scale
    return cx

def _heading_of(outline):
    if not outline or len(outline) < 2: return 0.0
    x0,y0=outline[0]; x1,y1=outline[1]
    return math.degrees(math.atan2(y1-y0, x1-x0))

def _signed_angle(part, code):
    if not isinstance(part.geometry, CurveGeometry): return 0.0
    a = abs(part.geometry.angle_degrees)
    pid = code or getattr(part, "id", "")
    if pid.endswith("R"): return -a
    if pid.endswith("L"): return a
    return float(part.geometry.angle_degrees)

def _offset(pose, half):
    hr = math.radians(pose.heading_degrees)
    nx, ny = -math.sin(hr), math.cos(hr)
    return pose.x + nx*half, pose.y + ny*half

def _step_curve(pose, radius, dt):
    hr = math.radians(pose.heading_degrees)
    ar = math.radians(dt)
    td = 1.0 if dt >= 0 else -1.0
    lx = radius * math.sin(abs(ar))
    ly = td * radius * (1.0 - math.cos(abs(ar)))
    wx = lx*math.cos(hr) - ly*math.sin(hr)
    wy = lx*math.sin(hr) + ly*math.cos(hr)
    return Pose(pose.x+wx, pose.y+wy, pose.heading_degrees+dt)

def piece_polygon(part, code, start, steps=8):
    g = part.geometry
    if isinstance(g, StraightGeometry):
        hr = math.radians(start.heading_degrees)
        end = Pose(start.x+g.length*math.cos(hr), start.y+g.length*math.sin(hr), start.heading_degrees)
        return [_offset(start,HALF_W),_offset(end,HALF_W),_offset(end,-HALF_W),_offset(start,-HALF_W)]
    if not isinstance(g, CurveGeometry):
        return [_offset(start,HALF_W), _offset(start,-HALF_W)]
    n=max(4,steps); dt=_signed_angle(part,code)/n; pose=start
    outer=[_offset(pose,HALF_W)]; inner=[_offset(pose,-HALF_W)]
    for _ in range(n):
        pose=_step_curve(pose,g.radius,dt)
        outer.append(_offset(pose,HALF_W)); inner.append(_offset(pose,-HALF_W))
    inner.reverse(); return outer+inner

def layout_pieces(sequence, get_part, start=None):
    codes=[c for c in sequence if get_part(c) is not None]
    parts=[get_part(c) for c in codes]
    origin=start or Pose(0.0,0.0,0.0)
    poses=compute_track_path(parts, start=origin) if parts else [origin]
    return [(code, piece_polygon(parts[i], code, poses[i])) for i,code in enumerate(codes)], poses

def keys_used(sequence):
    used={base_id(c) for c in sequence}
    return [(sku,label) for sku,label in COLOR_KEY if sku in used]

def _bounds(pieces, outline, pad=280.0):
    xs,ys=[],[]
    for _,poly in pieces:
        for x,y in poly: xs.append(x); ys.append(y)
    for x,y in outline or []: xs.append(x); ys.append(y)
    if not xs: return -pad,-pad,pad,pad
    return min(xs)-pad, min(ys)-pad, max(xs)+pad, max(ys)+pad

def _track_span(pieces, outline):
    xs,ys=[],[]
    for _,poly in pieces:
        for x,y in poly: xs.append(x); ys.append(y)
    for x,y in outline or []: xs.append(x); ys.append(y)
    if not xs: return 0.0,0.0,0.0,0.0,1.0,1.0
    return min(xs),min(ys),max(xs),max(ys),max(max(xs)-min(xs),1.0),max(max(ys)-min(ys),1.0)

def _rgb(sku):
    hx=PART_COLORS.get(base_id(sku),"7F8C8D")
    return int(hx[0:2],16), int(hx[2:4],16), int(hx[4:6],16)

def _hx_rgb(hx):
    hx = (hx or "7F8C8D").replace("#","")
    return int(hx[0:2],16), int(hx[2:4],16), int(hx[4:6],16)

def piece_fill_hexes(sequence, inventory=None):
    remaining = None
    if inventory is not None:
        remaining = {str(k): int(v or 0) for k, v in inventory.items()}
    out = []
    for code in sequence:
        sku = base_id(code)
        sku_col = PART_COLORS.get(sku, "7F8C8D")
        if remaining is None:
            out.append(sku_col)
            continue
        left = int(remaining.get(sku, 0) or 0)
        if left > 0:
            remaining[sku] = left - 1
            out.append(sku_col)
        else:
            out.append("000000")
    return out
