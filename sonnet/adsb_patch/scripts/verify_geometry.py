#!/usr/bin/env python3
"""Independent Gerber/drill checks and copper connectivity measurements."""
import json
import math
import re
from pathlib import Path
from collections import Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from gerbonara import GerberFile
from gerbonara.utils import MM
from shapely import make_valid
from shapely.geometry import Point, Polygon, LineString, shape
from shapely.ops import unary_union, polygonize
from extract_geometry import ROOT, polygons

def primitive_polygon(pr):
    kind = type(pr).__name__
    if kind == 'Circle':
        return Point(pr.x, -pr.y).buffer(pr.r, quad_segs=128)
    if kind == 'Line':
        return LineString([(pr.x1,-pr.y1),(pr.x2,-pr.y2)]).buffer(pr.width/2, quad_segs=64)
    if kind == 'Arc':
        raise ValueError('Arc stroke requires explicit handling; do not silently approximate')
    ap = pr if kind == 'ArcPoly' else pr.to_arc_poly()
    pts = []
    for p1,p2,(cw,center) in ap.segments:
        if cw is None:
            pts.append((p1[0],-p1[1]))
        else:
            cx,cy = center
            a = math.atan2(p1[1]-cy,p1[0]-cx)
            end = math.atan2(p2[1]-cy,p2[0]-cx)
            delta = (end-a) % (2*math.pi)
            if cw:
                delta = -((a-end) % (2*math.pi))
            r = math.dist(p1,center)
            n = max(2,math.ceil(abs(delta)*r/0.001))
            pts.extend((cx+r*math.cos(a+delta*i/n),-(cy+r*math.sin(a+delta*i/n))) for i in range(n))
    return make_valid(Polygon(pts))

def gerber_geometry(path):
    f = GerberFile.open(path)
    # Batch same-polarity primitives; preserve transitions in Gerber exposure order.
    g = Polygon()
    pending, polarity = [], True
    for obj in f.objects:
        for pr in obj.to_primitives(unit=MM):
            if pr.polarity_dark != polarity:
                group = unary_union(pending)
                g = g.union(group) if polarity else g.difference(group)
                pending,polarity = [],pr.polarity_dark
            pending.append(primitive_polygon(pr))
    group = unary_union(pending)
    return g.union(group) if polarity else g.difference(group)

def main():
    d = json.loads((ROOT/'geometry/extracted.json').read_text())
    layers = {name: shape(g) for name,g in d['layers'].items()}
    feed = next(v for v in d['vias'] if v['net']=='/1090_RF_IN')
    report = {'feed_via': feed, 'via_counts': dict(Counter(v['net'] for v in d['vias'])),
              'layer_checks': {}, 'drill_checks': []}
    edge_file=GerberFile.open(ROOT/'source/gerber/ads-b-Edge_Cuts.gbr')
    edge_lines=[]
    for obj in edge_file.objects:
        for pr in obj.to_primitives(unit=MM):
            if type(pr).__name__!='Line':raise ValueError('Unexpected curved profile; implement curve comparison')
            edge_lines.append(LineString([(pr.x1,-pr.y1),(pr.x2,-pr.y2)]))
    edge=unary_union(list(polygonize(edge_lines)))
    board=shape(d['outline'])
    report['outline_check']={'gerber_centerline_area_mm2':edge.area,
        'kicad_area_mm2':board.area,'symmetric_difference_mm2':board.symmetric_difference(edge).area,
        'hausdorff_mm':board.boundary.hausdorff_distance(edge.boundary)}
    # Gerbers describe planar copper before drilling. Apply the same physical holes.
    for name,g in layers.items():
        gb = gerber_geometry(ROOT/f'source/gerber/ads-b-{name.replace(".","_")}.gbr')
        holes = []
        order = list(layers)
        for v in d['vias']:
            if order.index(v['from']) <= order.index(name) <= order.index(v['to']):
                holes.append(Point(v['at']).buffer(v['drill_mm']/2,quad_segs=64))
        for p in d['pads']:
            if p['drill_mm'][0]:
                if p['drill_mm'][0] != p['drill_mm'][1]:
                    raise ValueError('Slotted drill: add an exact slot comparison')
                holes.append(Point(p['at']).buffer(p['drill_mm'][0]/2,quad_segs=64))
        gb = gb.difference(unary_union(holes)).intersection(shape(d['outline']))
        delta = g.symmetric_difference(gb)
        tolerance = 0.002
        significant = g.difference(gb.buffer(tolerance)).area + gb.difference(g.buffer(tolerance)).area
        report['layer_checks'][name] = {'kicad_area_mm2':g.area, 'gerber_area_mm2':gb.area,
            'symmetric_difference_mm2':delta.area, 'difference_outside_2um_mm2':significant,
            'pass_2um': significant < 0.001,
            'difference_outside_10um_mm2':g.difference(gb.buffer(.01)).area + gb.difference(g.buffer(.01)).area,
            'difference_outside_25um_mm2':g.difference(gb.buffer(.025)).area + gb.difference(g.buffer(.025)).area}
    for path in sorted((ROOT/'source/gerber').glob('*.drl')):
        tools,selected,hits = {},None,[]
        for line in path.read_text().splitlines():
            if m:=re.fullmatch(r'T(\d+)C([\d.]+)',line): tools[m[1]]=float(m[2])
            elif m:=re.fullmatch(r'T(\d+)',line): selected=m[1]
            elif m:=re.fullmatch(r'X(-?[\d.]+)Y(-?[\d.]+)',line):
                hits.append(([float(m[1]),-float(m[2])],tools[selected]))
        candidates = [v for v in d['vias'] if (v['from']=='F.Cu') == ('PTH.drl' in path.name and 'NPTH' not in path.name)]
        if 'NPTH' in path.name: candidates=[]
        errors=[]
        for v in candidates:
            error=min((math.dist(v['at'],pt) for pt,diam in hits if abs(diam-v['drill_mm'])<1e-6),default=math.inf)
            if error>0.001:errors.append({'via':v['uuid'],'error_mm':error})
        pads=[p for p in d['pads'] if p['drill_mm'][0] and 'PTH.drl' in path.name and 'NPTH' not in path.name]
        pad_errors=[]
        for pad in pads:
            error=min((math.dist(pad['at'],pt) for pt,diam in hits if abs(diam-pad['drill_mm'][0])<1e-6),default=math.inf)
            if error>.001:pad_errors.append({'pad':pad['reference']+':'+pad['number'],'error_mm':error})
        report['drill_checks'].append({'file':path.name,'hits':len(hits),'matched_vias':len(candidates)-len(errors),'unmatched_vias':errors,
            'matched_through_hole_pads':len(pads)-len(pad_errors),'unmatched_pads':pad_errors})
    top_patch = shape(next(z['fill'] for z in d['zones'] if z['layer']=='F.Cu'))
    feed_pad = Point(feed['at']).buffer(feed['pad_mm']/2,quad_segs=256)
    report['top_patch_to_feed_pad_clearance_mm'] = top_patch.distance(feed_pad)
    report['top_patch_electrically_touches_feed_pad'] = top_patch.intersects(feed_pad)
    report['patch_outline_mm'] = next(z['outline'] for z in d['zones'] if z['layer']=='F.Cu')
    report['board_bounds_mm'] = list(shape(d['outline']).bounds)
    (ROOT/'reports/geometry_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(2,2,figsize=(12,12))
    for ax,(name,g) in zip(axes.flat,layers.items()):
        for p in sorted(polygons(g),key=lambda p:p.area,reverse=True):
            x,y=p.exterior.xy;ax.fill(x,y,color='#b76e28')
            for h in p.interiors:
                x,y=h.xy;ax.fill(x,y,color='white')
        x,y=shape(d['outline']).exterior.xy;ax.plot(x,y,'k-',linewidth=.6)
        ax.plot(*feed['at'],'r+',markersize=8);ax.set_title(name)
        ax.set_aspect('equal');ax.invert_yaxis();ax.set_xlabel('KiCad X [mm]');ax.set_ylabel('KiCad Y [mm]')
    fig.tight_layout();fig.savefig(ROOT/'reports/copper_layers.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(10,10))
    for ax,(name,g) in zip(axes.flat,layers.items()):
        for p in sorted(polygons(g),key=lambda p:p.area,reverse=True):
            x,y=p.exterior.xy;ax.fill(x,y,color='#b76e28')
            for h in p.interiors:
                x,y=h.xy;ax.fill(x,y,color='white')
        x,y=feed['at'];ax.set_xlim(x-.9,x+.9);ax.set_ylim(y+.9,y-.9)
        ax.plot(x,y,'r+',markersize=8);ax.set_aspect('equal');ax.set_title(name+' — vía RF')
        ax.set_xlabel('KiCad X [mm]');ax.set_ylabel('KiCad Y [mm]')
    fig.tight_layout();fig.savefig(ROOT/'reports/feed_via_detail.png',dpi=180);plt.close(fig)
    text=['# Verificación geométrica','',f"Vía RF: {feed['at']} mm; pad {feed['pad_mm']} mm; taladro {feed['drill_mm']} mm.",
          f"Despeje medido entre pad y relleno F.Cu: {report['top_patch_to_feed_pad_clearance_mm']:.6f} mm.",
          '**El patch F.Cu no está unido galvánicamente al pad RF en el archivo fuente.** No se agregó cobre para corregirlo.',
          '', '| Capa | Área KiCad mm² | Área Gerber mm² | Diferencia fuera de 2 µm mm² | Coincide |',
          '|---|---:|---:|---:|---|']
    for n,c in report['layer_checks'].items():
        text.append(f"| {n} | {c['kicad_area_mm2']:.6f} | {c['gerber_area_mm2']:.6f} | {c['difference_outside_2um_mm2']:.6g} | {c['pass_2um']} |")
    text.extend(['','Se conservan los rellenos almacenados; no se ejecutó refill ni se guardó el PCB original.',
                 'Comparación de Gerbers después de restar taladros. El JSON contiene diferencias y cotejo de vías contra Excellon.',
                 f"Contorno Edge.Cuts contra línea central Gerber: diferencia de área {report['outline_check']['symmetric_difference_mm2']:.9g} mm²; distancia Hausdorff {report['outline_check']['hausdorff_mm']:.9g} mm.",
                 'Las comprobaciones geométricas no validan los sólidos dieléctricos ni la convergencia electromagnética.'])
    (ROOT/'reports/geometry_verification.md').write_text('\n'.join(text)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
