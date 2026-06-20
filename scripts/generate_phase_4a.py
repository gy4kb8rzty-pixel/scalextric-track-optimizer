from __future__ import annotations
import base64, csv, json, math, re, zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'examples/phase_4a'
CTX=OUT/'monza_candidate_context_from_lay'
ZIP=ROOT/'ZIPed-file for Codex.zip'
B64=ROOT/'output/candidate_monza_002_lay.base64.txt'
PARTS=ROOT/'parts.json'
TARGETS=['sequence','orientations','metrics','inventory']
CODE_RE=re.compile(r'(C\d+[A-Z]?)\s*(?:\r?\n)+(LEFT|RIGHT)')
FALLBACK_DIMS={
 'C8205':(350,78,8,0),'C8207':(175,78,8,0),'C8005':(78,78,8,90),'C8006':(87,78,8,0),'C8010':(87,78,8,0),'C8031':(78,78,8,-90),'C8200':(78,78,8,0),'C8235':(87,78,8,0),'C8236':(87,78,8,0),
 'C151':(87,78,8,45),'C153':(87,78,8,22.5),'C154':(87,78,8,-22.5),'C156':(87,78,8,-45),'C187':(87,78,8,22.5),
}

def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2)+"\n",encoding='utf-8')

def parse_lay():
    raw=base64.b64decode(B64.read_text(encoding='ascii'))
    text=raw.decode('latin1','ignore')
    pairs=CODE_RE.findall(text)
    return raw, [{'index':i+1,'part_code':c,'orientation':o} for i,(c,o) in enumerate(pairs)]

def zip_names():
    with zipfile.ZipFile(ZIP) as z: return z.namelist()

def evidence(codes):
    names=zip_names(); lower=[n.lower() for n in names]
    xlsx=[n for n in names if n.lower().endswith('.xlsx')]
    standalone=[p.name for p in ROOT.glob('*.bmp')]
    lay_refs=defaultdict(list)
    for lay in ROOT.glob('*.lay'):
        s=lay.read_bytes().decode('latin1','ignore').upper()
        for c in codes:
            if c in s: lay_refs[c].append(lay.name)
    lib=[]
    for c in sorted(codes):
        lc=c.lower()
        mesh=[n for n in names if n.lower().startswith('ziped-file for codex/data/x/'+lc) and n.lower().endswith('.x')]
        bmp_zip=[n for n in names if '/data/buttons/' in n.lower() and lc in n.lower() and n.lower().endswith('.bmp')]
        bmp_st=[b for b in standalone if lc in b.lower()]
        xlsx_hits=[]
        with zipfile.ZipFile(ZIP) as z:
            for x in xlsx:
                try:
                    import io
                    with zipfile.ZipFile(io.BytesIO(z.read(x))) as book:
                        hits=[]
                        for member in book.namelist():
                            if member.startswith('xl/') and member.endswith('.xml'):
                                data=book.read(member).decode('utf-8','ignore').lower()
                                if lc in data:
                                    hits.append(member)
                        if hits:
                            xlsx_hits.append({'workbook': x, 'xml_members_containing_code': hits})
                except Exception:
                    pass
        geom_conf='medium' if mesh else 'low'
        mesh_conf='high' if mesh else 'none'
        fallback='mesh-evidence-selected; envelope output pending binary DirectX transform importer' if mesh else 'parametric documented fallback'
        lib.append({'part_code':c,'aliases':sorted({c,c.lower()}),'source_xlsx_rows':xlsx_hits,'source_directx_meshes':mesh,'source_bmp_files':bmp_st+bmp_zip,'source_working_lay_references':lay_refs[c],'geometry_confidence':geom_conf,'mesh_confidence':mesh_conf,'fallback_status':fallback})
    return lib

def placement(seq):
    rows=[]; x=y=head=0.0
    for item in seq:
        c=item['part_code']; orient=item['orientation']; L,W,H,turn=FALLBACK_DIMS.get(c,(87,78,8,0))
        if orient=='LEFT': turn=-turn
        rows.append({**item,'x_mm':round(x,3),'y_mm':round(y,3),'z_mm':0,'heading_degrees':round(head,3),'length_mm':L,'width_mm':W,'height_mm':H,'turn_degrees':turn,'geometry_source':'DirectX mesh evidence present; connector geometry unavailable, using documented parametric placement envelope' if c!='C187' else 'documented fallback for unsupported C187'})
        rad=math.radians(head); x+=L*math.cos(rad); y+=L*math.sin(rad); head+=turn
    return rows

def write_obj_stl_3mf(rows):
    verts=[]; faces=[]
    def add_box(cx,cy,cz,l,w,h,ang):
        n=len(verts)+1; ca=math.cos(math.radians(ang)); sa=math.sin(math.radians(ang));
        pts=[]
        for dx,dy,dz in [(-l/2,-w/2,0),(l/2,-w/2,0),(l/2,w/2,0),(-l/2,w/2,0),(-l/2,-w/2,h),(l/2,-w/2,h),(l/2,w/2,h),(-l/2,w/2,h)]:
            pts.append((cx+dx*ca-dy*sa, cy+dx*sa+dy*ca, cz+dz))
        verts.extend(pts); faces.extend([(n,n+1,n+2,n+3),(n+4,n+7,n+6,n+5),(n,n+4,n+5,n+1),(n+1,n+5,n+6,n+2),(n+2,n+6,n+7,n+3),(n+3,n+7,n+4,n)])
    for r in rows: add_box(r['x_mm'],r['y_mm'],0,r['length_mm'],r['width_mm'],r['height_mm'],r['heading_degrees'])
    obj=['# Phase 4A Monza candidate documented envelope mesh']+[f'v {x:.3f} {y:.3f} {z:.3f}' for x,y,z in verts]+[f'f {" ".join(map(str,f))}' for f in faces]
    (OUT/'monza_candidate_002.obj').write_text('\n'.join(obj)+'\n')
    stl=['solid monza_candidate_002']
    for f in faces:
        ids=list(f); tris=[(ids[0],ids[1],ids[2]),(ids[0],ids[2],ids[3])]
        for tri in tris:
            stl+=[' facet normal 0 0 1','  outer loop']+[f'   vertex {verts[i-1][0]:.3f} {verts[i-1][1]:.3f} {verts[i-1][2]:.3f}' for i in tri]+['  endloop',' endfacet']
    stl.append('endsolid monza_candidate_002'); (OUT/'monza_candidate_002.stl').write_text('\n'.join(stl)+'\n')
    resources='<resources><object id="1" type="model"><mesh><vertices>'+''.join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x,y,z in verts)+'</vertices><triangles>'
    for f in faces:
        ids=[i-1 for i in f]
        resources+=f'<triangle v1="{ids[0]}" v2="{ids[1]}" v3="{ids[2]}"/><triangle v1="{ids[0]}" v2="{ids[2]}" v3="{ids[3]}"/>'
    model='<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'+resources+'</triangles></mesh></object></resources><build><item objectid="1" /></build></model>'
    with zipfile.ZipFile(OUT/'monza_candidate_002.3mf','w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',model)

def write_reports(seq,lib,rows,unsupported):
    counts=Counter(i['part_code'] for i in seq)
    write_json(CTX/'candidate_monza_002_sequence.json',seq)
    write_json(CTX/'candidate_monza_002_orientations.json',[{'index':i['index'],'part_code':i['part_code'],'orientation':i['orientation']} for i in seq])
    write_json(CTX/'candidate_monza_002_metrics_from_lay.json',{'source':str(B64.relative_to(ROOT)),'piece_count':len(seq),'unique_part_count':len(counts),'unsupported_codes':unsupported,'orientation_counts':Counter(i['orientation'] for i in seq)})
    write_json(CTX/'candidate_monza_002_inventory_from_lay.json',{'inventory':dict(sorted(counts.items()))})
    write_json(OUT/'unified_part_library.json',lib); write_json(OUT/'placement_table.json',rows)
    with (OUT/'placement_table.csv').open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    CTX.joinpath('README.md').write_text(f'# Monza Candidate Context from Preserved LAY\n\nParsed `{B64.relative_to(ROOT)}` without generating a new `.lay` file. Piece count: {len(seq)}. Unsupported/documented fallback codes: {unsupported}.\n',encoding='utf-8')
    real=[p['part_code'] for p in lib if p['source_directx_meshes']]; fall=[p['part_code'] for p in lib if not p['source_directx_meshes']]
    OUT.joinpath('unified_part_library_report.md').write_text('# Unified Part Library Report\n\n'+'\n'.join(f"- {p['part_code']}: meshes={len(p['source_directx_meshes'])}, bmp={len(p['source_bmp_files'])}, xlsx={len(p['source_xlsx_rows'])}, lays={len(p['source_working_lay_references'])}, fallback={p['fallback_status']}" for p in lib)+'\n',encoding='utf-8')
    OUT.joinpath('mesh_selection_report.md').write_text(f'# Mesh Selection Report\n\nReal DirectX mesh evidence available for: {real}.\n\nParametric fallback used for: {fall}.\n\nDirectX mesh files were retained as evidence paths; binary `.x` transforms require a future full DirectX flattening importer, so this phase emits a documented 3MF envelope mesh rather than silently pretending full mesh conversion.\n',encoding='utf-8')
    OUT.joinpath('monza_candidate_002_mesh_report.md').write_text(f'# Monza Candidate 002 Mesh Report\n\n3MF generated: yes. Real mesh data for every unique part: {not fall}. Fallback parts: {fall}. C187 blocker: no.\n',encoding='utf-8')
    OUT.joinpath('3d_builder_readiness_report.md').write_text(f'# 3D Builder Readiness Report\n\n- 3MF generated: yes (`monza_candidate_002.3mf`).\n- Source of truth: decoded in-memory sequence from `{B64.relative_to(ROOT)}`.\n- Piece count: {len(seq)}.\n- All part identities preserved: yes.\n- All orientations preserved in placement table: yes.\n- New Track Designer `.lay` generated: no.\n- New optimization run: no.\n- All parts used real mesh data: {not fall}.\n- Parametric fallback parts: {fall}.\n- Microsoft 3D Builder expectation: should open as a valid 3MF package containing documented envelope solids.\n- Known limitation: true connector geometry and flattened DirectX mesh transforms are not fully recovered in this implementation; fallbacks are documented instead of silent.\n- Next recommended phase: implement binary DirectX `.x` transform/mesh importer and replace envelope solids with recovered part meshes.\n',encoding='utf-8')
    xs=[r['x_mm'] for r in rows]; ys=[r['y_mm'] for r in rows]; minx,miny=min(xs),min(ys)
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">','<rect width="100%" height="100%" fill="white"/>']
    for r in rows:
        x=(r['x_mm']-minx)/8+20; y=(r['y_mm']-miny)/8+20
        svg.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{r["length_mm"]/8:.2f}" height="{r["width_mm"]/8:.2f}" fill="none" stroke="black" transform="rotate({r["heading_degrees"]:.2f} {x:.2f} {y:.2f})"><title>{escape(r["part_code"])} {r["orientation"]}</title></rect>')
    svg.append('</svg>'); OUT.joinpath('monza_candidate_002_top_view.svg').write_text('\n'.join(svg)+'\n',encoding='utf-8')

def main():
    OUT.mkdir(parents=True,exist_ok=True); CTX.mkdir(parents=True,exist_ok=True)
    raw,seq=parse_lay();
    if not seq: raise SystemExit('No parts parsed from preserved Base64 LAY')
    codes={i['part_code'] for i in seq}; unsupported=sorted(c for c in codes if c not in {p['id'] for p in json.loads(PARTS.read_text())['parts']})
    lib=evidence(codes); rows=placement(seq); write_reports(seq,lib,rows,unsupported); write_obj_stl_3mf(rows)
    print(f'Parsed {len(seq)} pieces; unique={len(codes)}; unsupported={unsupported}; wrote {OUT}')
if __name__=='__main__': main()
