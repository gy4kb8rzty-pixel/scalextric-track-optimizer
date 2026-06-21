from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'examples/phase_4e'
P4B=ROOT/'examples/phase_4b'

def readj(p): return json.loads(p.read_text())
def writej(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2)+'\n')

def main():
    db=readj(P4B/'geometry_database.json')
    inv=readj(P4B/'best_monza_candidate.json')['inventory_usage']
    c153=next(p for p in db['parts'] if p['track_code']=='C153')
    dims=c153['dimensions_mm']
    c187={
      'track_code':'C187','part_classification':'available_composite_curve',
      'geometry_rule':'two consecutive C153 sections','radius_source':'C153 chain',
      'angle_degrees':45.0,'inventory_count':7,
      'component_sequence':['C153','C153'],
      'dimensions_mm':{'length':round(dims['length']*2,3),'width':dims['width'],'height':dims['height']},
      'connectors':c153['connectors'],'source_3mf':'composite:C153+C153',
      'status':'available_geometry_composite_not_fallback'
    }
    writej(OUT/'c187_geometry_support.json',c187)
    report=['# Phase 4E C187 Support','','C187 is treated as available geometry, not missing geometry and not fallback-required.','','| Item | Value |','|---|---|',
      '| Geometry rule | two consecutive C153 sections |','| Radius | same as C153 chain |','| Angle | 45 degrees |',f"| Inventory | {inv.get('C187',0)} pieces |",'| Missing geometry | NO |','| Fallback-required | NO |','| Can participate in optimization | YES |']
    (OUT/'phase_4e_c187_support_report.md').write_text('\n'.join(report)+'\n')
    print('Phase 4E complete: C187 available as C153+C153 composite')
if __name__=='__main__': main()
