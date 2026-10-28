#!/usr/bin/env python3
"""Check geometry after Sonnet's native save, independently of generation."""
import argparse
import json
import re
import xml.etree.ElementTree as E
from pathlib import Path
from shapely.geometry import Polygon,shape
from shapely.ops import unary_union
from extract_geometry import ROOT

def main():
    ap=argparse.ArgumentParser();ap.add_argument('case',nargs='?',default='A_real');args=ap.parse_args()
    manifest=json.loads((ROOT/f'models/{args.case}.json').read_text())
    d=json.loads((ROOT/'geometry/extracted.json').read_text())
    root=E.parse(ROOT/f'models/{args.case}_ready.sonx').getroot()
    ns={'s':'https://www.sonnetsoftware.com/schema/project'}
    shift=manifest['shift_from_kicad_mm'];checks={}
    for layer in root.findall('.//s:PlanarTechLayer',ns):
        polys=[]
        for el in layer.findall('s:Objects/s:PlanarPolygon',ns):
            pts=' '.join(p.text or '' for p in el.findall('s:Points',ns))
            coords=[(float(x)-shift[0],float(y)-shift[1]) for x,y in re.findall(r'\(([^,]+),([^\)]+)\)',pts)]
            polys.append(Polygon(coords))
        expected=shape(d['layers'][layer.get('Name')]);actual=unary_union(polys)
        area=expected.symmetric_difference(actual).area
        checks[layer.get('Name')]={'symmetric_difference_mm2':area,'pass':area<1e-4}
    ports=[p for p in root.findall('.//s:Geometry//s:Port',ns) if p.get('Number') is not None]
    checks['port_numbers']={'pass':sorted(int(p.get('Number')) for p in ports)==[-1,1]}
    checks['impedance_50ohm']={'pass':all(float(p.find('s:Impedance',ns).get('Resistance'))==50 for p in ports)}
    checks['floating_ground']={'pass':all(p.find('s:Type/s:GndRef',ns).get('Type')=='FLOAT' for p in ports)}
    covers=root.findall('.//s:BoxCover',ns)
    checks['open_covers']={'pass':len(covers)==2 and all(c.get('MaterialType')=='FREE_SPACE' for c in covers)}
    deembed=root.find('s:Control/s:DeEmbed',ns)
    # 19.54 omits this element when false (confirmed with runmacro -m).
    checks['deembedding_off']={'pass':deembed is None or deembed.get('On')=='FALSE'}
    vias=root.findall('.//s:ViaPolygon',ns)
    checks['barrel_count']={'actual':len(vias),'pass':len(vias)==manifest['barrels_including_plated_pads']}
    checks['hollow_barrels']={'pass':all(m.get('Solid')=='FALSE' and m.get('ModelType')=='VOLUME'
        for m in root.findall('.//s:ViaMaterialModel',ns))}
    checks['passes_all']=all(v['pass'] for v in checks.values())
    (ROOT/f'reports/{args.case}_xml_verification.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(checks,indent=2))
    if not checks['passes_all']:raise SystemExit(1)

if __name__=='__main__':main()
