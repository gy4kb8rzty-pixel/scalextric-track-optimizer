"""SVG/PNG/PDF drawing for plan_view."""
from __future__ import annotations
import io, math, struct, zlib
from monza_optimizer.catalog.parts import base_id
from monza_optimizer.export.threemf_builder import PART_COLORS
from monza_optimizer.export.plan_view import (
    layout_pieces, keys_used, _bounds, _track_span, _heading_of, _tick_step,
    _space_label, _blit_text, _rgb, _hx_rgb, piece_fill_hexes, INK, RED,
)
from monza_optimizer.geometry.pose import Pose

def render_svg(sequence, get_part, title="Layout", outline_points=None):
    outline=list(outline_points or [])
    pieces,_=layout_pieces(sequence,get_part,start=Pose(0.0,0.0,_heading_of(outline)))
    minx,miny,maxx,maxy=_bounds(pieces,outline)
    tx0,ty0,tx1,ty1,tw,th=_track_span(pieces,outline)
    w=max(maxx-minx,1.0); h=max(maxy-miny,1.0)
    vw,vh=900.0, max(280.0, 900.0*h/w+56); scale=vw/w
    def xy(x,y): return (x-minx)*scale, vh-56-(y-miny)*scale
    paths=[]
    for sku,poly in pieces:
        pts=" ".join(f"{xy(x,y)[0]:.1f},{xy(x,y)[1]:.1f}" for x,y in poly)
        col="#"+PART_COLORS.get(base_id(sku),"7F8C8D")
        paths.append(f'<polygon points="{pts}" fill="{col}" fill-opacity="0.88" stroke="#1f2933" stroke-width="1.1"/>')
    if len(outline)>=2:
        d=" ".join(f"{xy(x,y)[0]:.1f},{xy(x,y)[1]:.1f}" for x,y in outline)
        paths.append(f'<polyline points="{d}" fill="none" stroke="#c0392b" stroke-width="2.4" stroke-linejoin="round"/>')
    ax0,ay0=xy(tx0,ty0); ax1,ay1=xy(tx1,ty0); ay_top=xy(tx0,ty1)[1]
    paths.append(f'<line x1="{ax0:.1f}" y1="{ay0:.1f}" x2="{ax1:.1f}" y2="{ay1:.1f}" stroke="#111" stroke-width="2.2"/>')
    paths.append(f'<line x1="{ax0:.1f}" y1="{ay0:.1f}" x2="{ax0:.1f}" y2="{ay_top:.1f}" stroke="#111" stroke-width="2.2"/>')
    t=0.0; step=_tick_step(tw)
    while t<=tw+1:
        px,py=xy(tx0+t,ty0)
        paths.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{py+8:.1f}" stroke="#111" stroke-width="1.6"/>')
        paths.append(f'<text x="{px:.1f}" y="{py+20:.1f}" text-anchor="middle" font-size="10" font-family="sans-serif">{int(round(t/1000.0))}m</text>')
        t+=step
    t=0.0; step=_tick_step(th)
    while t<=th+1:
        px,py=xy(tx0,ty0+t)
        paths.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px-8:.1f}" y2="{py:.1f}" stroke="#111" stroke-width="1.6"/>')
        paths.append(f'<text x="{px-12:.1f}" y="{py+4:.1f}" text-anchor="end" font-size="10" font-family="sans-serif">{int(round(t/1000.0))}m</text>')
        t+=step
    legend=[]; x=16.0
    legend.append(f'<line x1="{x}" y1="{vh-38}" x2="{x+18}" y2="{vh-38}" stroke="#c0392b" stroke-width="3"/>')
    legend.append(f'<text x="{x+22}" y="{vh-33}" font-size="12" font-family="sans-serif">Target</text>')
    x+=90
    names={"STR":"Straight","HALF":"Half","QTR":"Quarter","SHORT":"Short","R2":"R2 45","R2.22":"R2 22.5","R3":"R3","R4":"R4","R1":"R1","BANK":"Banked","CHIC":"Chicane"}
    for sku,label in keys_used(sequence):
        col="#"+PART_COLORS.get(sku,"7F8C8D"); shown=names.get(label,label)
        legend.append(f'<rect x="{x:.0f}" y="{vh-45:.0f}" width="14" height="14" fill="{col}" stroke="#222"/>')
        legend.append(f'<text x="{x+18:.0f}" y="{vh-33:.0f}" font-size="12" font-family="sans-serif">{shown}</text>')
        x += 18+7*len(shown)+16
    legend.append(f'<text x="16" y="{vh-12}" font-size="12" font-family="sans-serif">SPACE {_space_label(tw, th)}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:.0f} {vh:.0f}" width="900" height="{vh:.0f}">' f'<rect width="100%" height="100%" fill="#f7f4ee"/>' f'<text x="16" y="22" font-size="16" font-family="sans-serif">{title}</text>' + "".join(paths)+"".join(legend)+"</svg>")

def render_png(sequence, get_part, size=900, outline_points=None):
    outline=list(outline_points or [])
    pieces,_=layout_pieces(sequence,get_part,start=Pose(0.0,0.0,_heading_of(outline)))
    minx,miny,maxx,maxy=_bounds(pieces,outline)
    tx0,ty0,tx1,ty1,tw,th=_track_span(pieces,outline)
    w=max(maxx-minx,1.0); h=max(maxy-miny,1.0)
    canvas=size; top,bot=22,80
    scale=(canvas-24-top-bot)/max(w,h)
    img=bytearray([247,244,238]*(canvas*canvas))
    def put(ix,iy,rgb):
        if 0<=ix<canvas and 0<=iy<canvas:
            o=(iy*canvas+ix)*3; img[o:o+3]=bytes(rgb)
    def pix(x,y):
        return int(12+(x-minx)*scale), int(canvas-bot-8-(y-miny)*scale)
    for sku,poly in pieces:
        col=_rgb(sku); pts=[pix(x,y) for x,y in poly]
        _fill_poly(pts, lambda ix,iy: put(ix,iy,col))
        for i,(x0,y0) in enumerate(pts):
            x1,y1=pts[(i+1)%len(pts)]
            _line(x0,y0,x1,y1, lambda ix,iy: put(ix,iy,(30,30,30)))
    if len(outline)>=2:
        opts=[pix(x,y) for x,y in outline]
        for i in range(len(opts)-1):
            _line(opts[i][0],opts[i][1],opts[i+1][0],opts[i+1][1], lambda ix,iy: put(ix,iy,RED))
            _line(opts[i][0],opts[i][1]+1,opts[i+1][0],opts[i+1][1]+1, lambda ix,iy: put(ix,iy,RED))
    a=pix(tx0,ty0); b=pix(tx1,ty0); c=pix(tx0,ty1)
    _line(a[0],a[1],b[0],b[1], lambda ix,iy: put(ix,iy,INK))
    _line(a[0],a[1],c[0],c[1], lambda ix,iy: put(ix,iy,INK))
    t=0.0
    while t<=tw+1:
        p=pix(tx0+t,ty0)
        _line(p[0],p[1],p[0],p[1]+7, lambda ix,iy: put(ix,iy,INK))
        _blit_text(put, p[0]-6, p[1]+10, f"{int(round(t/1000.0))}M", INK, 1)
        t+=_tick_step(tw)
    t=0.0
    while t<=th+1:
        p=pix(tx0,ty0+t)
        _line(p[0],p[1],p[0]-7,p[1], lambda ix,iy: put(ix,iy,INK))
        _blit_text(put, max(2,p[0]-28), p[1]-4, f"{int(round(t/1000.0))}M", INK, 1)
        t+=_tick_step(th)
    ly=canvas-64; lx=8
    for dx in range(14):
        put(lx+dx, ly+6, RED); put(lx+dx, ly+7, RED)
    lx=_blit_text(put, lx+18, ly, "TARGET", INK, 2)+16
    for sku,label in keys_used(sequence):
        col=_rgb(sku)
        for dx in range(12):
            for dy in range(12): put(lx+dx, ly+dy, col)
        lx=_blit_text(put, lx+16, ly, label, INK, 2)+14
        if lx>canvas-80:
            lx=8; ly+=20
    _blit_text(put, 8, canvas-22, "SPACE "+_space_label(tw,th), INK, 2)
    return _png_rgb(canvas, canvas, bytes(img))

def _line(x0,y0,x1,y1,plot):
    steps=max(abs(x1-x0),abs(y1-y0),1)
    for s in range(steps+1):
        t=s/steps; plot(int(x0+(x1-x0)*t), int(y0+(y1-y0)*t))

def _fill_poly(pts, plot):
    if len(pts)<3: return
    ys=[p[1] for p in pts]
    for y in range(min(ys), max(ys)+1):
        xs=[]; n=len(pts)
        for i in range(n):
            x0,y0=pts[i]; x1,y1=pts[(i+1)%n]
            if y0==y1: continue
            if (y0<=y<y1) or (y1<=y<y0):
                xs.append(int(x0+(y-y0)/(y1-y0)*(x1-x0)))
        xs.sort()
        for i in range(0,len(xs)-1,2):
            for x in range(xs[i], xs[i+1]+1): plot(x,y)

def _png_rgb(width,height,raw):
    rows=b""; rb=width*3
    for y in range(height): rows += b"\x00"+raw[y*rb:(y+1)*rb]
    comp=zlib.compress(rows,9)
    def chunk(tag,data):
        crc=zlib.crc32(tag+data)&0xFFFFFFFF
        return struct.pack(">I",len(data))+tag+data+struct.pack(">I",crc)
    ihdr=struct.pack(">IIBBBBB",width,height,8,2,0,0,0)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",ihdr)+chunk(b"IDAT",comp)+chunk(b"IEND",b"")

def render_pdf(sequence, get_part, title, lay_text, outline_points=None, inventory=None):
    del lay_text
    outline=list(outline_points or [])
    pieces,_=layout_pieces(sequence,get_part,start=Pose(0.0,0.0,_heading_of(outline)))
    fills=piece_fill_hexes(sequence, inventory)
    minx,miny,maxx,maxy=_bounds(pieces,outline)
    tx0,ty0,tx1,ty1,tw,th=_track_span(pieces,outline)
    w=max(maxx-minx,1.0); h=max(maxy-miny,1.0)
    pw,ph=595.0,842.0; box_x,box_y,box_w,box_h=48.0,110.0,500.0,640.0
    scale=min(box_w/w, box_h/h)
    def xy(x,y): return box_x+(x-minx)*scale, box_y+(y-miny)*scale
    ops=["0.97 0.96 0.93 rg", f"0 0 {pw:.0f} {ph:.0f} re f"]
    safe_title=title.replace("(","[").replace(")","]")[:80]
    ops.append("0 0 0 rg")
    ops.append("BT /F1 14 Tf 36 812 Td ("+_pdf_esc(safe_title)+") Tj ET")
    for i,(sku,poly) in enumerate(pieces):
        hx=fills[i] if i < len(fills) else PART_COLORS.get(base_id(sku),"7F8C8D")
        r,g,b=[c/255 for c in _hx_rgb(hx)]
        ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg 0.12 0.12 0.14 RG 0.6 w")
        x0,y0=xy(*poly[0]); ops.append(f"{x0:.1f} {y0:.1f} m")
        for x,y in poly[1:]:
            xx,yy=xy(x,y); ops.append(f"{xx:.1f} {yy:.1f} l")
        ops.append("h B")
    if len(outline)>=2:
        ops.append("0.75 0.22 0.17 RG 1.6 w")
        x0,y0=xy(*outline[0]); ops.append(f"{x0:.1f} {y0:.1f} m")
        for x,y in outline[1:]:
            xx,yy=xy(x,y); ops.append(f"{xx:.1f} {yy:.1f} l")
        ops.append("S")
    ax0,ay0=xy(tx0,ty0); ax1,_=xy(tx1,ty0); ay_top=xy(tx0,ty1)[1]
    ops.append("0.05 0.05 0.05 RG 1.3 w")
    ops.append(f"{ax0:.1f} {ay0:.1f} m {ax1:.1f} {ay0:.1f} l S")
    ops.append(f"{ax0:.1f} {ay0:.1f} m {ax0:.1f} {ay_top:.1f} l S")
    t=0.0
    while t<=tw+1:
        px,py=xy(tx0+t,ty0)
        ops.append(f"{px:.1f} {py:.1f} m {px:.1f} {py-7:.1f} l S")
        ops.append("0 0 0 rg")
        ops.append(f"BT /F1 8 Tf {px-8:.1f} {py-18:.1f} Td ({int(round(t/1000.0))}m) Tj ET")
        ops.append("0.05 0.05 0.05 RG 1.3 w"); t+=_tick_step(tw)
    t=0.0
    while t<=th+1:
        px,py=xy(tx0,ty0+t)
        ops.append(f"{px:.1f} {py:.1f} m {px-7:.1f} {py:.1f} l S")
        ops.append("0 0 0 rg")
        ops.append(f"BT /F1 8 Tf {px-28:.1f} {py-3:.1f} Td ({int(round(t/1000.0))}m) Tj ET")
        ops.append("0.05 0.05 0.05 RG 1.3 w"); t+=_tick_step(th)
    ops.append("0 0 0 rg")
    note="Red = target circuit. Colour key = parts."
    if inventory is not None and any(h=="000000" for h in fills):
        note="Red = target. Black = still to buy."
    ops.append("BT /F1 9 Tf 36 54 Td ("+_pdf_esc(note)+") Tj ET")
    x=36.0
    ops.append("0.75 0.22 0.17 RG 2 w")
    ops.append(f"{x:.1f} 41 m {x+16:.1f} 41 l S")
    ops.append("0 0 0 rg")
    ops.append(f"BT /F1 8 Tf {x+20:.1f} 38 Td (Target) Tj ET"); x+=70
    names={"STR":"Straight","HALF":"Half","QTR":"Quarter","SHORT":"Short","R2":"R2 45","R2.22":"R2 22.5","R3":"R3","R4":"R4","R1":"R1","BANK":"Banked","CHIC":"Chicane"}
    for sku,label in keys_used(sequence):
        r,g,b=[c/255 for c in _rgb(sku)]; shown=names.get(label,label)
        ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.1f} 36 10 10 re f")
        ops.append("0 0 0 rg")
        ops.append(f"BT /F1 8 Tf {x+14:.1f} 38 Td ({_pdf_esc(shown)}) Tj ET")
        x += 14+6*len(shown)+10
        if x>520: break
    ops.append("0 0 0 rg")
    ops.append(f"BT /F1 10 Tf 36 20 Td ({_pdf_esc('Floor space '+_space_label(tw,th))}) Tj ET")
    stream="\n".join(ops).encode("latin-1","replace")
    objs=[b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
          b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
          (f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {pw:.0f} {ph:.0f}] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n").encode(),
          b"4 0 obj << /Length "+str(len(stream)).encode()+b" >> stream\n"+stream+b"\nendstream endobj\n",
          b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"]
    out=io.BytesIO(); out.write(b"%PDF-1.4\n"); offsets=[0]
    for obj in objs:
        offsets.append(out.tell()); out.write(obj)
    xref=out.tell()
    out.write(f"xref\n0 {len(objs)+1}\n".encode()); out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]: out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()

def _pdf_esc(s):
    return s.replace("\\","\\\\").replace("(","\\(").replace(")","\\)")
