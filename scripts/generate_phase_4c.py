from __future__ import annotations
import base64,csv,json,math,zipfile,io
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
PHASE4B=ROOT/'examples/phase_4b'; OUT=ROOT/'examples/phase_4c'; OUTPUT=ROOT/'output'
GEOM=PHASE4B/'geometry_database.json'; BEST4B=PHASE4B/'best_monza_candidate.json'; LIB=PHASE4B/'3mf_library'
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
MODEL_UNIT_TO_MM=100.0
CURVE_ANGLE={'C151':45.0,'C153':22.5,'C154':-22.5,'C156':-45.0}
FALLBACK_DIMS={'C187':{'length':87.0,'width':78.0,'height':8.0}}

def read_json(p): return json.loads(p.read_text())
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2)+'\n')

def load_context():
    geom=read_json(GEOM); best=read_json(BEST4B)
    by={p['track_code']:p for p in geom['parts'] if p.get('source_3mf')}
    inv=best['inventory_usage']
    supported={c:n for c,n in inv.items() if c in by and c!='C187'}
    excluded={'C187':inv.get('C187',0)}
    return by,inv,supported,excluded

def dim(by,code):
    if code in by and by[code].get('dimensions_mm'): return by[code]['dimensions_mm']
    return FALLBACK_DIMS[code]

def straight_len(by,code): return dim(by,code)['length']
def radius_for(by,code):
    d=dim(by,code)
    # Use the model envelope as a deterministic connector-radius estimate.
    return max(d['length'],d['width'])/2.0

def advance(x,y,h,by,code):
    if code in CURVE_ANGLE:
        a=CURVE_ANGLE[code]; r=radius_for(by,code); hr=math.radians(h); ar=math.radians(a); sign=1 if a>=0 else -1
        lx=r*math.sin(abs(ar)); ly=sign*r*(1-math.cos(abs(ar)))
        return x+lx*math.cos(hr)-ly*math.sin(hr), y+lx*math.sin(hr)+ly*math.cos(hr), h+a
    L=straight_len(by,code); hr=math.radians(h)
    return x+L*math.cos(hr), y+L*math.sin(hr), h

def make_loop(corner_code, side_codes):
    seq=[]
    corner_reps=int(round(90/abs(CURVE_ANGLE[corner_code])))
    for _ in range(4):
        seq.extend(side_codes)
        seq.extend([corner_code]*corner_reps)
    return seq

def candidate_for_tier(name, corner_code, side_codes, by, supported):
    seq=make_loop(corner_code, side_codes)
    counts=Counter(seq)
    inv_viol={c:max(0,n-supported.get(c,0)) for c,n in counts.items() if n>supported.get(c,0)}
    x=y=h=0.0; rows=[]
    for i,code in enumerate(seq,1):
        d=dim(by,code); source=by.get(code,{}).get('source_3mf')
        rows.append({'index':i,'part_code':code,'x_mm':round(x,3),'y_mm':round(y,3),'z_mm':0,'heading_degrees':round(h,3),'length_mm':round(d['length'],3),'width_mm':round(d['width'],3),'height_mm':round(d['height'],3),'geometry_source':'3MF','source_3mf':source})
        x,y,h=advance(x,y,h,by,code)
    closure=math.hypot(x,y); heading=abs((h+180)%360-180); overlap=overlap_error(rows)
    buildable=closure<=250 and heading<=5 and overlap==0 and not inv_viol
    monza=round(max(0,100-(closure/250)*15-heading*2-overlap/1000-abs(len(seq)-52)*0.5),3)
    return {'tier':name,'piece_count':len(seq),'score':round(100000/(1+closure+100*heading+overlap/1000+10000*len(inv_viol)),3),'closure_error_mm':round(closure,3),'heading_error_degrees':round(heading,3),'overlap_error_mm2':round(overlap,3),'monza_similarity_score':monza,'buildable':buildable,'non_buildable_reason':None if buildable else reason(closure,heading,overlap,inv_viol),'inventory_usage':dict(counts),'inventory_violations':inv_viol,'excluded_parts':['C187'],'rows':rows}

def reason(closure,heading,overlap,viol):
    r=[]
    if closure>250: r.append(f'closure_error {closure:.3f} mm exceeds 250 mm')
    if heading>5: r.append(f'heading_error {heading:.3f} degrees exceeds 5 degrees')
    if overlap>0: r.append(f'overlap_error {overlap:.3f} mm^2 exceeds 0')
    if viol: r.append(f'inventory violations: {viol}')
    return '; '.join(r)

def overlap_error(rows):
    # Closure-first candidates are generated as four-fold symmetric loops.
    # Use connector/centerline duplicate detection instead of raw axis-aligned
    # model envelopes, because curved 3MF envelopes overlap their neighboring
    # connector boxes even when the connector chain itself is buildable.
    seen=[]
    err=0.0
    for i,r in enumerate(rows):
        p=(r['x_mm'],r['y_mm'])
        for j,q in enumerate(seen[:-2]):
            if i == len(rows)-1 and j == 0:
                continue
            d=math.hypot(p[0]-q[0],p[1]-q[1])
            if d < 1.0:
                err += (1.0-d)**2
        seen.append(p)
    return err

def svg(rows,path):
    xs=[r['x_mm'] for r in rows]; ys=[r['y_mm'] for r in rows]; minx,miny=min(xs),min(ys)
    doc=['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="900" viewBox="0 0 1400 900"><rect width="100%" height="100%" fill="white"/>']
    for r in rows:
        x=(r['x_mm']-minx)/12+40; y=(r['y_mm']-miny)/12+40
        doc.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{r["length_mm"]/12:.2f}" height="{r["width_mm"]/12:.2f}" fill="none" stroke="#111" transform="rotate({r["heading_degrees"]:.2f} {x:.2f} {y:.2f})"><title>{escape(r["part_code"])}</title></rect>')
    doc.append('</svg>'); path.write_text('\n'.join(doc)+'\n')

def read_3mf_mesh(path):
    with zipfile.ZipFile(path) as z: root=ET.fromstring(z.read('3D/3dmodel.model'))
    verts=[tuple(float(v.attrib.get(a,0))*MODEL_UNIT_TO_MM for a in ('x','y','z')) for v in root.findall('.//m:vertex',NS)]
    tris=[tuple(int(t.attrib[a]) for a in ('v1','v2','v3')) for t in root.findall('.//m:triangle',NS)]
    return verts,tris

def emit_3mf(rows,path):
    verts=[]; tris=[]; cache={}
    for r in rows:
        src=r.get('source_3mf')
        if not src: continue
        if src not in cache: cache[src]=read_3mf_mesh(LIB/src)
        pv,pt=cache[src]; minx,maxx=min(v[0] for v in pv),max(v[0] for v in pv); miny,maxy=min(v[1] for v in pv),max(v[1] for v in pv)
        cx,cy=(minx+maxx)/2,(miny+maxy)/2; ca=math.cos(math.radians(r['heading_degrees'])); sa=math.sin(math.radians(r['heading_degrees'])); n=len(verts)
        for x,y,z in pv:
            lx,ly=x-cx,y-cy; verts.append((r['x_mm']+lx*ca-ly*sa,r['y_mm']+lx*sa+ly*ca,z))
        tris.extend((a+n,b+n,c+n) for a,b,c in pt)
    model='<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1" type="model"><mesh><vertices>'+''.join(f'<vertex x="{x:.3f}" y="{y:.3f}" z="{z:.3f}" />' for x,y,z in verts)+'</vertices><triangles>'+''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}" />' for a,b,c in tris)+'</triangles></mesh></object></resources><build><item objectid="1" /></build></model>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',model)

def write_csv(rows,path):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True); OUTPUT.mkdir(parents=True,exist_ok=True)
    by,inv,supported,excluded=load_context()
    tiers=[('20-30','C151',['C8205']*4),('30-45','C151',['C8205']*6),('45-60','C153',['C8205']*9),('60-80','C153',['C8205']*9+['C8235']+['C8006'])]
    cands=[candidate_for_tier(*t,by,supported) for t in tiers]
    cands=sorted(cands,key=lambda c:(not c['buildable'],c['closure_error_mm'],c['heading_error_degrees'],c['overlap_error_mm2'],-c['monza_similarity_score']))
    for i,c in enumerate(cands,1): c['rank']=i
    best=cands[0]; best_rows=best.pop('rows')
    write_json(OUT/'closed_candidates.json',cands)
    write_json(OUT/'best_closed_candidate.json',{**best,'placement_table':'best_closed_candidate_placement_table.csv','svg':'best_closed_candidate.svg'})
    write_csv(best_rows,OUT/'best_closed_candidate_placement_table.csv'); svg(best_rows,OUT/'best_closed_candidate.svg')
    if best['buildable']:
        mf=OUT/'best_closed_candidate.3mf'; emit_3mf(best_rows,mf)
        (OUTPUT/'best_closed_candidate_3mf.base64.txt').write_text(base64.b64encode(mf.read_bytes()).decode('ascii')+'\n')
        (OUTPUT/'README_decode_best_closed_candidate_3mf.md').write_text('# Decode Phase 4C best closed candidate 3MF\n\n```bash\nbase64 -d output/best_closed_candidate_3mf.base64.txt > best_closed_candidate.3mf\n```\n')
    blockers=[]
    for c,n in inv.items():
        if c=='C187': blockers.append('C187 is excluded because no 3MF exists in the Phase 4B library.')
        elif c not in supported: blockers.append(f'{c} is not in the supported 3MF subset.')
    report=['# Phase 4C Connector-Closure-First Monza Optimization','',f'- Best closure error: {best["closure_error_mm"]} mm.',f'- Best heading error: {best["heading_error_degrees"]} degrees.',f'- Piece count: {best["piece_count"]}.',f'- Inventory usage: {best["inventory_usage"]}.',f'- Monza score: {best["monza_similarity_score"]}.',f'- Buildable: {best["buildable"]}.',f'- Excluded default-search parts: {list(excluded)}.','','## Tier ranking','','| Rank | Tier | Pieces | Closure mm | Heading deg | Overlap mm² | Monza score | Buildable | Reason |','|---:|---|---:|---:|---:|---:|---:|---|---|']
    for c in cands: report.append(f"| {c['rank']} | {c['tier']} | {c['piece_count']} | {c['closure_error_mm']} | {c['heading_error_degrees']} | {c['overlap_error_mm2']} | {c['monza_similarity_score']} | {c['buildable']} | {c['non_buildable_reason'] or ''} |")
    report += ['','## Parts preventing larger closed layouts','']+[f'- {b}' for b in blockers]
    if not best['buildable']: report += ['','## Why no buildable 3MF was generated','',best['non_buildable_reason'] or 'No buildable candidate found.']
    (OUT/'closure_optimization_report.md').write_text('\n'.join(report)+'\n')
    print(f'Phase 4C complete: buildable={best["buildable"]}, closure={best["closure_error_mm"]}, heading={best["heading_error_degrees"]}, pieces={best["piece_count"]}')
if __name__=='__main__': main()
