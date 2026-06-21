from __future__ import annotations
import base64,csv,json,math,re,zipfile,io
from collections import Counter,defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'examples/phase_4b'; EXTRACT=OUT/'3mf_library'
ZIP=ROOT/'all_x_3mf_rotated_full_parser.zip'; XLSX=ROOT/'Scalextric_Masterkatalog_Allomfattande_med_3MF.xlsx'
SEQ4A=ROOT/'examples/phase_4a/monza_candidate_context_from_lay/candidate_monza_002_sequence.json'
B64=ROOT/'output/candidate_monza_002_lay.base64.txt'
CODE_RE=re.compile(r'(C\d+[A-Z]?)\s*(?:\r?\n)+(LEFT|RIGHT)')
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
MODEL_UNIT_TO_MM=100.0  # Parser 3MF coordinates are centimeters; convert to millimeters.

def code_from_name(n):
    m=re.match(r'(?i)(c\d+[a-z]?)',Path(n).stem)
    if not m: return Path(n).stem.upper()
    s=m.group(1).upper()
    # strip view suffixes to canonical track code
    for suf in ('LP','RP','L','R','P','A','B'):
        if s.endswith(suf) and len(s) > len(suf) + 3:
            return s[:-len(suf)]
    return s


def classify_part(code, rec=None):
    if code == 'C8205':
        return 'standard_straight'
    if code == 'C187':
        return 'missing_3mf_fallback_required'
    dims=(rec or {}).get('dimensions_mm') or {}
    if dims.get('length',0) > 200 and dims.get('width',0) <= 180:
        return 'standard_straight'
    if code.startswith(('C15','C70')):
        return 'curve_or_lane_change'
    return 'special_or_accessory'

def extract_and_index():
    OUT.mkdir(parents=True,exist_ok=True); EXTRACT.mkdir(parents=True,exist_ok=True)
    index=[]
    with zipfile.ZipFile(ZIP) as z:
        for name in z.namelist():
            if not name.lower().endswith('.3mf'): continue
            data=z.read(name); dest=EXTRACT/Path(name).name; dest.write_bytes(data)
            bbox=parse_3mf_bbox(data)
            code=code_from_name(name)
            index.append({'track_code':code,'source_3mf':name,'extracted_3mf':str(dest.relative_to(ROOT)),**bbox})
    return index

def parse_3mf_bbox(data):
    verts,_=read_3mf_mesh(data)
    if not verts:
        return {'vertex_count':0,'bbox':None,'dimensions_mm':None,'connectors':[]}
    xs,ys,zs=zip(*verts); mn=(min(xs),min(ys),min(zs)); mx=(max(xs),max(ys),max(zs))
    dims=(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2])
    # Connector estimate from actual model geometry: midpoint of the two end faces along the longest XY axis.
    axis=0 if dims[0]>=dims[1] else 1
    c1=[(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2]; c2=c1.copy(); c1[axis]=mn[axis]; c2[axis]=mx[axis]
    return {'vertex_count':len(verts),'bbox':{'min_mm':[round(x,3) for x in mn],'max_mm':[round(x,3) for x in mx]},'dimensions_mm':{'length':round(max(dims[0],dims[1]),3),'width':round(min(dims[0],dims[1]),3),'height':round(dims[2],3),'x':round(dims[0],3),'y':round(dims[1],3),'z':round(dims[2],3)},'connectors':[{'name':'A','position_mm':[round(x,3) for x in c1]},{'name':'B','position_mm':[round(x,3) for x in c2]}]}

def read_3mf_mesh(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml=z.read('3D/3dmodel.model')
    root=ET.fromstring(xml); verts=[]; tris=[]
    for v in root.findall('.//m:vertex',NS):
        verts.append(tuple(float(v.attrib.get(a,0))*MODEL_UNIT_TO_MM for a in ('x','y','z')))
    for t in root.findall('.//m:triangle',NS):
        tris.append(tuple(int(t.attrib[a]) for a in ('v1','v2','v3')))
    return verts,tris

def read_xlsx_rows():
    rows=[]
    with zipfile.ZipFile(XLSX) as book:
        shared=[]
        if 'xl/sharedStrings.xml' in book.namelist():
            r=ET.fromstring(book.read('xl/sharedStrings.xml'))
            for si in r.findall('.//{*}si'):
                shared.append(''.join(t.text or '' for t in si.findall('.//{*}t')))
        sheets=[n for n in book.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
        for sheet in sheets:
            root=ET.fromstring(book.read(sheet))
            for row in root.findall('.//{*}row'):
                vals=[]
                for c in row.findall('{*}c'):
                    v=c.find('{*}v'); val=v.text if v is not None else ''
                    if c.attrib.get('t')=='s' and val.isdigit(): val=shared[int(val)]
                    vals.append(val)
                txt=' '.join(vals)
                m=re.search(r'(?i)\bC\d{3,5}[A-Z]?\b',txt)
                if m: rows.append({'track_code':m.group(0).upper(),'sheet':sheet,'values':vals})
    return rows

def load_sequence():
    if SEQ4A.exists(): return json.loads(SEQ4A.read_text())
    text=base64.b64decode(B64.read_text()).decode('latin1','ignore')
    return [{'index':i+1,'part_code':c,'orientation':o} for i,(c,o) in enumerate(CODE_RE.findall(text))]

def place(seq, geom_by_code, mirror=1, scale=1.0):
    rows=[]; x=y=h=0.0
    for it in seq:
        g=geom_by_code.get(it['part_code']) or {}
        d=g.get('dimensions_mm') or {'length':87,'width':78,'height':8}
        L=d['length']*scale; W=d['width']; H=d['height']; orient=it.get('orientation','RIGHT')
        turn=0.0
        if it['part_code'].startswith(('C15','C70')) and L<200: turn=22.5 if orient=='RIGHT' else -22.5
        turn*=mirror
        rows.append({**it,'x_mm':round(x,3),'y_mm':round(y,3),'z_mm':0,'heading_degrees':round(h,3),'length_mm':round(L,3),'width_mm':round(W,3),'height_mm':round(H,3),'turn_degrees':turn,'scale':scale,'geometry_source':'3MF' if g else 'fallback_missing_3mf','source_3mf':g.get('source_3mf')})
        rad=math.radians(h); x+=L*math.cos(rad); y+=L*math.sin(rad); h+=turn
    closure=math.hypot(x,y); heading=abs((h+180)%360-180)
    return rows,closure,heading

def overlap_error(rows):
    err=0.0
    boxes=[]
    for r in rows:
        boxes.append((r['x_mm']-r['length_mm']/2,r['y_mm']-r['width_mm']/2,r['x_mm']+r['length_mm']/2,r['y_mm']+r['width_mm']/2))
    for i,a in enumerate(boxes):
        for b in boxes[i+2:]:
            ix=max(0,min(a[2],b[2])-max(a[0],b[0])); iy=max(0,min(a[3],b[3])-max(a[1],b[1])); err+=ix*iy
    return round(err,3)

def emit_3mf(rows,path):
    verts=[]; tris=[]; mesh_cache={}
    for r in rows:
        source=r.get('source_3mf')
        if source and source not in mesh_cache:
            mesh_cache[source]=read_3mf_mesh((EXTRACT/Path(source).name).read_bytes())
        part_verts,part_tris=mesh_cache.get(source, ([], []))
        if not part_verts:
            continue
        minx=min(v[0] for v in part_verts); maxx=max(v[0] for v in part_verts); miny=min(v[1] for v in part_verts); maxy=max(v[1] for v in part_verts)
        cx=(minx+maxx)/2; cy=(miny+maxy)/2; ca=math.cos(math.radians(r['heading_degrees'])); sa=math.sin(math.radians(r['heading_degrees']))
        n=len(verts)
        for x,y,z in part_verts:
            lx=(x-cx)*r.get('scale',1.0); ly=y-cy
            verts.append((r['x_mm']+lx*ca-ly*sa,r['y_mm']+lx*sa+ly*ca,z))
        tris.extend((a+n,b+n,c+n) for a,b,c in part_tris)
    model='<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1" type="model"><mesh><vertices>'+''.join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x,y,z in verts)+'</vertices><triangles>'+''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a,b,c in tris)+'</triangles></mesh></object></resources><build><item objectid="1" /></build></model>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'); z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'); z.writestr('3D/3dmodel.model',model)

def main():
    idx=extract_and_index(); xrows=read_xlsx_rows(); by= {}
    for rec in idx: by.setdefault(rec['track_code'],rec)
    catalog=defaultdict(list)
    for r in xrows: catalog[r['track_code']].append(r)
    seq=load_sequence(); seq_codes=sorted({i['part_code'] for i in seq}); missing_codes=[c for c in seq_codes if c not in by]
    geom=[]
    for code,rec in sorted(by.items()):
        geom.append({**rec,'part_classification':classify_part(code,rec),'catalog_rows':len(catalog.get(code,[]))})
    for code in missing_codes:
        geom.append({'track_code':code,'source_3mf':None,'extracted_3mf':None,'vertex_count':0,'bbox':None,'dimensions_mm':None,'connectors':[],'part_classification':classify_part(code),'catalog_rows':len(catalog.get(code,[])),'status':'missing_3mf_geometry'})
    candidates=[]
    for mirror in (1,-1):
      for scale in (0.96,0.98,1.0,1.02,1.04):
        rows,closure,heading=place(seq,by,mirror,scale); ov=overlap_error(rows); score=round(100000/(1+closure+20*heading+ov/1000),3)
        candidates.append({'rank':0,'score':score,'scale':scale,'mirror':mirror,'closure_error_mm':round(closure,3),'heading_error_degrees':round(heading,3),'overlap_error_mm2':ov,'piece_count':len(rows),'inventory_usage':dict(Counter(r['part_code'] for r in rows)),'geometric_accuracy':'uses real 3MF mesh dimensions where mapped; missing 3MF codes are marked fallback-required and excluded from 3MF mesh preview','missing_3mf_codes':missing_codes,'rows':rows})
    candidates=sorted(candidates,key=lambda c:c['score'],reverse=True)[:10]
    for i,c in enumerate(candidates,1): c['rank']=i
    best=candidates[0]; rows=best.pop('rows')
    (OUT/'geometry_database.json').write_text(json.dumps({'source_zip':ZIP.name,'source_xlsx':XLSX.name,'models_indexed':len(idx),'catalog_rows_read':len(xrows),'missing_3mf_codes_in_monza_sequence':missing_codes,'parts':geom},indent=2)+'\n')
    (OUT/'monza_top_10_solutions.json').write_text(json.dumps(candidates,indent=2)+'\n')
    (OUT/'best_monza_candidate.json').write_text(json.dumps({**best,'data_sources':{'geometry_database':'geometry_database.json','source_3mf_zip':ZIP.name,'source_catalog':XLSX.name,'monza_sequence':str(SEQ4A.relative_to(ROOT))},'generated_artifacts':['placement_table.csv','placement_table.json','monza_top_view.svg','monza_candidate_3mf_preview.3mf','monza_top_10_solutions.json','monza_optimization_report.md'],'placement_table':'placement_table.json'},indent=2)+'\n')
    (OUT/'placement_table.json').write_text(json.dumps(rows,indent=2)+'\n')
    with (OUT/'placement_table.csv').open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    xs=[r['x_mm'] for r in rows]; ys=[r['y_mm'] for r in rows]; minx,miny=min(xs),min(ys)
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="900" viewBox="0 0 1400 900"><rect width="100%" height="100%" fill="white"/>']
    for r in rows:
        x=(r['x_mm']-minx)/5+30; y=(r['y_mm']-miny)/5+30
        svg.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{r["length_mm"]/5:.2f}" height="{r["width_mm"]/5:.2f}" fill="none" stroke="#111" transform="rotate({r["heading_degrees"]:.2f} {x:.2f} {y:.2f})"><title>{escape(r["part_code"])} {escape(str(r.get("source_3mf")))}</title></rect>')
    svg.append('</svg>'); (OUT/'monza_top_view.svg').write_text('\n'.join(svg)+'\n')
    emit_3mf(rows,OUT/'monza_candidate_3mf_preview.3mf')
    report=['# Phase 4B Full 3MF-Based Monza Optimization','',f'- Models extracted and indexed: {len(idx)}.',f'- Catalog rows read from workbook: {len(xrows)}.',f'- Best score: {best["score"]}.',f'- Closure error: {best["closure_error_mm"]} mm.',f'- Heading error: {best["heading_error_degrees"]} degrees.',f'- Overlap error: {best["overlap_error_mm2"]} mm².',f'- Missing 3MF codes in Monza sequence: {missing_codes}.','- C8205 classification: standard_straight (not crossover).','','## Top 10','']
    for c in candidates: report.append(f"{c['rank']}. score={c['score']} closure={c['closure_error_mm']}mm overlap={c['overlap_error_mm2']}mm² scale={c['scale']} mirror={c['mirror']} missing_3mf={c['missing_3mf_codes']}")
    report += ['','## Inventory usage','']+[f'- {k}: {v}' for k,v in sorted(best['inventory_usage'].items())]
    report += ['','## 3MF availability corrections','','- C187: missing from `all_x_3mf_rotated_full_parser.zip`; placement uses fallback dimensions and the preview 3MF excludes real C187 mesh geometry.','- C8205: standard straight track geometry from `c8205.3mf`; not classified as crossover.']
    (OUT/'monza_optimization_report.md').write_text('\n'.join(report)+'\n')
    mapping=['# Phase 4B 3MF Mapping Report','','| Track code | Classification | 3MF file | Status |','|---|---|---|---|']
    for rec in sorted(geom,key=lambda r:r['track_code']):
        status=rec.get('status') or ('mapped_3mf' if rec.get('source_3mf') else 'missing_3mf_geometry')
        mapping.append(f"| {rec['track_code']} | {rec.get('part_classification')} | {rec.get('source_3mf') or ''} | {status} |")
    (OUT/'3mf_mapping_report.md').write_text('\n'.join(mapping)+'\n')
    classifications=['# Phase 4B Part Classification Report','','- C8205 is classified as `standard_straight`, not crossover.','- C187 is classified as `missing_3mf_fallback_required` because no C187 3MF exists in the current library.','','| Track code | Classification | Evidence |','|---|---|---|']
    for code in sorted(best['inventory_usage']):
        rec=by.get(code)
        evidence=rec.get('source_3mf') if rec else 'missing from 3MF library'
        classifications.append(f"| {code} | {classify_part(code,rec)} | {evidence} |")
    (OUT/'part_classification_report.md').write_text('\n'.join(classifications)+'\n')
    readiness=['# Phase 4B Owned-Inventory Readiness','','| Track code | Required count | 3MF readiness | Notes |','|---|---:|---|---|']
    for code,count in sorted(best['inventory_usage'].items()):
        ready='ready' if code in by else 'fallback-required'
        note='standard straight; not crossover' if code=='C8205' else ('no 3MF in current library' if code=='C187' else '')
        readiness.append(f"| {code} | {count} | {ready} | {note} |")
    (OUT/'owned_inventory_readiness.md').write_text('\n'.join(readiness)+'\n')
    print(f'Phase 4B complete: {len(idx)} models, best score {best["score"]}, missing 3MF {missing_codes}, wrote {OUT}')
if __name__=='__main__': main()
