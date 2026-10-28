#!/usr/bin/env python3
"""Read-only KiCad extraction. Run with the supplied system-site-packages venv."""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

import pcbnew as k
from shapely import make_valid
from shapely.geometry import Polygon, Point, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parents[2]

def polygons(g):
    if g.geom_type == 'Polygon':
        yield g
    elif hasattr(g, 'geoms'):
        for sub in g.geoms:
            yield from polygons(sub)

def polyset(s):
    def points(chain):
        return [(chain.CPoint(i).x / 1e6, chain.CPoint(i).y / 1e6)
                for i in range(chain.PointCount())]
    return unary_union([make_valid(Polygon(points(s.Outline(i)),
                       [points(s.Hole(i, j)) for j in range(s.HoleCount(i))]))
                       for i in range(s.OutlineCount())])

def pos(p):
    return [p.x / 1e6, p.y / 1e6]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pcb', type=Path, default=WORK / 'PCB/1-ADS-B/Final/ads-b/ads-b.kicad_pcb')
    args = ap.parse_args()
    for d in ['source', 'source/gerber', 'geometry', 'reports']:
        (ROOT/d).mkdir(parents=True, exist_ok=True)
    for ext in ['kicad_pcb', 'kicad_pro', 'kicad_sch']:
        src = args.pcb.with_suffix('.' + ext)
        if src.resolve() != (ROOT/'source'/src.name).resolve():
            shutil.copy2(src, ROOT/'source'/src.name)
    for src in sorted((args.pcb.parent/'gerber').glob('*')):
        if src.suffix in {'.gbr', '.drl', '.gbrjob'}:
            dst = ROOT/'source/gerber'/src.name
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
    b = k.LoadBoard(str(args.pcb))
    # Conversion tolerance only, in memory. Stored zone fills remain untouched.
    b.GetDesignSettings().m_MaxError = 250  # 0.25 um chord tolerance
    layers = list(b.GetEnabledLayers().CuStack())
    outline = k.SHAPE_POLY_SET()
    if not b.GetBoardPolygonOutlines(outline, False):
        raise RuntimeError('PCB outline is not closed')
    board = polyset(outline)
    data = {'units': 'mm', 'kicad_version': k.GetBuildVersion(), 'curve_chord_error_mm': .00025,
            'outline': mapping(board), 'layers': {}, 'vias': [], 'pads': [], 'tracks': [], 'zones': []}
    for t in b.GetTracks():
        if isinstance(t, k.PCB_VIA):
            data['vias'].append({'uuid': t.m_Uuid.AsString(), 'net': t.GetNetname(),
                'at': pos(t.GetPosition()), 'pad_mm': t.GetWidth(t.TopLayer())/1e6,
                'drill_mm': t.GetDrillValue()/1e6,
                'from': b.GetLayerName(t.TopLayer()), 'to': b.GetLayerName(t.BottomLayer())})
        else:
            data['tracks'].append({'net': t.GetNetname(), 'layer': b.GetLayerName(t.GetLayer()),
                'start': pos(t.GetStart()), 'end': pos(t.GetEnd()), 'width_mm': t.GetWidth()/1e6})
    for f in b.GetFootprints():
        for pad in f.Pads():
            data['pads'].append({'reference': f.GetReference(), 'number': pad.GetNumber(),
                'net': pad.GetNetname(), 'at': pos(pad.GetPosition()), 'size_mm': pos(pad.GetSize()),
                'drill_mm': pos(pad.GetDrillSize()),
                'plated': pad.GetAttribute() == k.PAD_ATTRIB_PTH,
                'layers': [b.GetLayerName(l) for l in layers if pad.IsOnLayer(l)]})
    for z in b.Zones():
        data['zones'].append({'net': z.GetNetname(), 'layer': b.GetLayerName(z.GetLayer()),
            'outline': mapping(polyset(z.Outline())),
            'fill': mapping(polyset(z.GetFilledPolysList(z.GetLayer())))})
    # KiCad's board converter includes stored zone fills, tracks, pad shapes, vias,
    # and copper graphics. Holes are subtracted explicitly, without re-filling zones.
    for l in layers:
        ps = k.SHAPE_POLY_SET()
        b.ConvertBrdLayerToPolygonalContours(l, ps)
        copper = polyset(ps)
        holes = []
        for via in data['vias']:
            if layers.index(l) in range(layers.index(b.GetLayerID(via['from'])),
                                       layers.index(b.GetLayerID(via['to']))+1):
                holes.append(Point(via['at']).buffer(via['drill_mm']/2, quad_segs=64))
        for pad in b.GetPads():
            if pad.GetDrillSize().x:
                hp = k.SHAPE_POLY_SET()
                pad.TransformHoleToPolygon(hp, 0, 1000, k.ERROR_INSIDE)
                holes.append(polyset(hp))
        copper = copper.difference(unary_union(holes)).intersection(board)
        data['layers'][b.GetLayerName(l)] = mapping(copper)
    (ROOT/'geometry/extracted.json').write_text(json.dumps(data, indent=2))
    files = {str(p.relative_to(ROOT/'source')): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted((ROOT/'source').rglob('*')) if p.is_file()}
    manifest = {'repository': 'https://github.com/beam-ttm/PCB', 'branch': 'main',
                'pcb_git_blob': subprocess.check_output(['git','hash-object',str(args.pcb)], text=True).strip(),
                'remote_main_pcb_blob_verified': '14dfc0d47c17186fb33b4abe7bb53a42ed9653eb',
                'sha256': files}
    (ROOT/'source_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    job = json.loads((ROOT/'source/gerber/ads-b-job.gbrjob').read_text())
    stack = {'source': 'source/gerber/ads-b-job.gbrjob', 'layers': job['MaterialStackup'],
             'nominal_total_mm': job['GeneralSpecs']['BoardThickness'],
             'dielectric_tan_delta': 0.0,
             'tan_delta_status': 'KiCad declares zero: lossless baseline, NOT verified physical loss',
             'copper_conductivity_S_m': 5.8e7, 'copper_status': 'bulk smooth copper assumption; not a foil certificate',
             'via_plating_mm': 0.025, 'via_plating_status': 'ASSUMPTION; absent from KiCad and drill files',
             'soldermask_model': 'omitted: dielectric properties unavailable',
             'finite_substrate_model': 'Sonnet uniform dielectric extends to box walls'}
    (ROOT/'stackup.json').write_text(json.dumps(stack, indent=2)+'\n')
    print('Extracted', {n: len(list(polygons(__import__('shapely').geometry.shape(g)))) for n,g in data['layers'].items()})

if __name__ == '__main__':
    main()
