#!/usr/bin/env python3
"""Generate Sonnet 19.54 XML using the installed examples' element structure."""
import argparse
import copy
import json
import math
import xml.etree.ElementTree as E
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from shapely.geometry import shape, Point, LineString
from shapely.ops import split, unary_union
from extract_geometry import ROOT, polygons

NS = 'https://www.sonnetsoftware.com/schema/project'
E.register_namespace('',NS)
E.register_namespace('xsi','http://www.w3.org/2001/XMLSchema-instance')

def node(parent,tag,text=None,**attrs):
    el=E.SubElement(parent,'{'+NS+'}'+tag,{k:str(v) for k,v in attrs.items()})
    if text is not None:el.text=str(text)
    return el

def set_project_header(root, stamp=None):
    """Persist revision dates: absent headers get new dates on each Sonnet read."""
    stamp=stamp or datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%m/%d/%Y %H:%M:%S')
    existing=root.find('{'+NS+'}Header')
    if existing is not None:root.remove(existing)
    header=E.Element('{'+NS+'}Header')
    node(node(header,'Created',Program='adsb_generator',Version='1.0'),'Date',stamp)
    modified=node(header,'Modified',Program='adsb_generator',Version='1.0')
    node(modified,'Date',stamp)
    for importance in ['MEDIUM','HIGH']:
        node(node(modified,'Change',Importance=importance),'Date',stamp)
    root.insert(1,header)
    return stamp

def pieces(poly):
    """Split through holes; preserve copper exactly without filling clearances."""
    if not poly.interiors:
        yield poly
        return
    hole=poly.interiors[0]
    x=__import__('shapely').geometry.Polygon(hole).representative_point().x
    parts=list(polygons(split(poly,LineString([(x,poly.bounds[1]-1),(x,poly.bounds[3]+1)]))))
    if len(parts)<2:raise RuntimeError('Cannot split polygon hole safely')
    for part in parts:yield from pieces(part)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--template',type=Path,default=ROOT/'source/blank.sonx')
    ap.add_argument('--box-mm',type=float,default=1600.)
    ap.add_argument('--cell-mm',type=float,default=.05)
    ap.add_argument('--air-mm',type=float,default=40.)
    ap.add_argument('--tan-delta',type=float,default=None)
    ap.add_argument('--variant',choices=['A_real','B_no_rf_barrel','C_rf_wall_010','C_rf_wall_035'],default='A_real')
    ap.add_argument('--name')
    args=ap.parse_args()
    if args.box_mm <= 100 or args.cell_mm<=0 or args.air_mm<=0:ap.error('Invalid box/grid/air')
    d=json.loads((ROOT/'geometry/extracted.json').read_text())
    stack=json.loads((ROOT/'stackup.json').read_text())
    dielectrics=[s for s in stack['layers'] if s['Type']=='Dielectric']
    copper=[s for s in stack['layers'] if s['Type']=='Copper']
    if len(dielectrics)!=3 or len(copper)!=4:raise ValueError('Expected a four-copper-layer stack')
    eps=[float(str(s['DielectricConstant']).replace(',','.')) for s in dielectrics]
    foil=[s['Thickness'] for s in copper]
    root=E.parse(args.template).getroot()
    q=lambda s:'{'+NS+'}'+s
    for tag in ['StartupGraphs']:
        el=root.find(q(tag))
        if el is not None:root.remove(el)
    set_project_header(root)
    root.find(q('Units')).find(q('Length')).text='MM'
    control=root.find(q('Control'))
    control.find(q('DeEmbed')).set('On','FALSE')
    node(control,'Currents',On='TRUE')
    geo=root.find(q('Geometry'));geo.clear();geo.set('YDirection','Negative')
    tand=stack['dielectric_tan_delta'] if args.tan_delta is None else args.tan_delta
    for ident,name,er,tan in [('air','Air',1,0),('d1','JLC2116_top',eps[0],tand),
                              ('d2','JLC_Core',eps[1],tand),('d3','JLC2116_bottom',eps[2],tand)]:
        material=node(geo,'Dielectric',MacroID=ident,Name=name,LossType='CONDUCTIVITY',Anisotropic='FALSE')
        node(material,'FrequencyModel',ModelType='None',RefFreq='0',ValidRef='FALSE')
        for tag,value in [('Conductivity',0),('Eps',er),('Tan',tan),('MuRel',1),('MagLossTan',0)]:
            node(material,tag,Value=value)
    node(geo,'Conductor',MacroID='copper',Name='Copper',Conductivity=stack['copper_conductivity_S_m'],LossType='CONDUCTIVITY')
    box=node(geo,'Box')
    for ident,typ in [('top_cover','TOP'),('bot_cover','BOTTOM')]:
        node(box,'BoxCover',MacroID=ident,Type=typ,MaterialType='FREE_SPACE',Roughness='0',Thickness='0')
    # Planar sheets at copper midplanes: dielectric gap plus half of each adjacent foil.
    intervals=[dielectrics[i]['Thickness']+(foil[i]+foil[i+1])/2 for i in range(3)]
    node(box,'Size',X=args.box_mm,Y=args.box_mm,Z=2*args.air_mm+sum(intervals))
    nc=round(args.box_mm/args.cell_mm)
    if abs(nc*args.cell_mm-args.box_mm)>1e-8:ap.error('Box must contain an integer number of cells')
    node(box,'NumCells',X=nc,Y=nc);node(box,'LocalOrigin',X=0,Y=args.box_mm);node(box,'Symmetry',On='FALSE')
    bb=shape(d['outline']).bounds
    shift=(args.box_mm/2-(bb[0]+bb[2])/2,args.box_mm/2-(bb[1]+bb[3])/2)
    names=list(d['layers']);objects={};counter=1;counts={};planar=[]
    for i,(name,mat,thick,cu) in enumerate(zip(names+['bottom_air'],
            ['Air','JLC2116_top','JLC_Core','JLC2116_bottom','Air'],
            [args.air_mm]+intervals+[args.air_mm],foil+[0])):
        lev=node(geo,'Level',MacroID=f'lev{i}',MaterialName=mat,Number=i)
        node(lev,'DielectricMaterialModel',Thickness=thick)
        if i==4:continue
        layer=node(node(lev,'Objects'),'PlanarTechLayer',MacroID=f'cu{i}',Name=name,MaterialName='Copper')
        node(layer,'ColorPattern',Color=['#b76e28','#cc9933','#889933','#338899'][i],Pattern='updiag')
        node(layer,'PlanarMaterialModel',CurrentRatio='.5',ModelType='THIN_METAL',Thickness=cu)
        node(layer,'RoughnessModel',RoughnessOn='FALSE')
        # Hole-preserving polygon splits share long edges and source contours
        # contain micron-scale segments; use the robust rectangular mesher.
        node(layer,'PlanarMeshing',EnableMesh='TRUE',FillType='RECTANGULAR')
        node(layer,'SubsectionMeshing',XMin=1,XMax=100,YMin=1,YMax=100,EdgeMeshed='TRUE',DiagonalEdges='FALSE',AnisotropicType='X_AND_Y')
        node(layer,'GLGMeshing',GLG='FALSE');obj=node(layer,'Objects')
        src=shape(d['layers'][name]);ps=[s for p in polygons(src) for s in pieces(p)]
        error=unary_union(ps).symmetric_difference(src).area
        if error>1e-6:raise RuntimeError(f'Polygon splitting changes area: {name}: {error}')
        counts[name]={'polygons':len(ps),'split_area_error_mm2':error,'area_mm2':src.area}
        for p in ps:
            coords=list(p.exterior.coords)[:-1]
            el=node(obj,'PlanarPolygon',MacroID=f'p{counter}',Id=counter);counter+=1
            node(el,'Points',' '.join(f'({x+shift[0]:.9f},{y+shift[1]:.9f})' for x,y in coords))
            if name=='B.Cu':planar.append((el,coords))
    # Floating local source between the D1 signal pad edge and the adjacent
    # real GND copper boundary. D1 itself is not populated in the EM model.
    selected=[]
    for number,target in [(1,(78.5,85.6)),(-1,(78.38,85.8005))]:
        options=[]
        for el,coords in planar:
            for edge,(a,b) in enumerate(zip(coords,coords[1:]+coords[:1])):
                if abs(a[1]-b[1])<1e-8 and .1<math.dist(a,b)<.8:
                    mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
                    options.append((math.dist(mid,target),el,edge,mid))
        distance,el,edge,mid=min(options,key=lambda o:o[0])
        if distance>.1:raise RuntimeError(f'Cannot locate exact D1 pad edge: {number}: {distance}')
        obj=el.find(q('Objects'))
        if obj is None:obj=node(el,'Objects')
        port=node(obj,'Port',MacroID='rf_positive' if number==1 else 'rf_return',Number=number,Vertex=edge)
        typ=node(port,'Type',Type='COUPLED',AutoGroupName='Auto')
        node(typ,'GndRef',Type='FLOAT');node(typ,'TerminalWidth',Type='FEED')
        node(port,'Impedance',Resistance=50,Reactance=0,Inductance=0,Capacitance=0)
        node(port,'Center',f'({mid[0]+shift[0]:.9f},{mid[1]+shift[1]:.9f})')
        node(port,'CoupledGroup',Name='Auto')
        selected.append({'number':number,'kicad_center_mm':mid,'polygon_id':el.get('Id'),'edge':edge})
    via_count=0
    barrels=d['vias']+[{'net':p['net'],'at':p['at'],'drill_mm':p['drill_mm'][0],
                       'from':names[0],'to':names[-1]}
                      for p in d['pads'] if p.get('plated') and p['drill_mm'][0]]
    for i,v in enumerate(barrels):
        rf=v['net']=='/1090_RF_IN'
        if rf and args.variant=='B_no_rf_barrel':continue
        wall=stack['via_plating_mm']
        if rf and args.variant=='C_rf_wall_010':wall=.010
        if rf and args.variant=='C_rf_wall_035':wall=.035
        vi=node(geo,'ViaTechLayer',MacroID=f'vt{i}',Name=f'via_{i}',MaterialName='Copper')
        node(vi,'ColorPattern',Color='#bb44dd' if rf else '#888888',Pattern='updiag')
        node(vi,'ViaMaterialModel',ModelType='VOLUME',Solid='FALSE',Thickness=wall)
        node(vi,'ViaMeshing',AutoHeight='FALSE',EnableMesh='TRUE',FillType='RING',HasPads='FALSE')
        node(vi,'GLGMeshing',GLG='FALSE')
        node(vi,'ViaLevels',FromLevel=names.index(v['from']),FromType='LEVEL',ToLevel=names.index(v['to']),ToType='LEVEL')
        poly=node(node(vi,'Objects'),'ViaPolygon',MacroID=f'v{i}',Id=counter);counter+=1
        # Finished bore diameter + two assumed plating walls, not pad diameter.
        radius=v['drill_mm']/2+wall
        x,y=v['at']
        sides=max(32,math.ceil(math.pi/math.acos(1-min(.001/radius,.1))))
        coords=[(x+radius*math.cos(2*math.pi*j/sides),y+radius*math.sin(2*math.pi*j/sides)) for j in range(sides)]
        node(poly,'Points',' '.join(f'({a+shift[0]:.9f},{b+shift[1]:.9f})' for a,b in coords))
        via_count+=1
    sw=root.find(q('Sweeps'));sw.clear();sw.set('SweepVariables','FALSE')
    freqs=node(node(sw,'Set',MacroID='sweep',On='TRUE'),'Frequencies')
    node(freqs,'Sweep',MacroID='band',Type='ABS_ENTRY',On='TRUE',Adaptive='TRUE',Start='.8',Stop='1.4',Target=300)
    node(freqs,'Sweep',MacroID='f1090',Type='STEP',On='TRUE',Adaptive='FALSE',Start='1.09')
    out=root.find(q('OutputFiles'));out.clear();out.set('Folder','.')
    name=args.name or args.variant
    dest=ROOT/f'models/{name}.sonx';dest.parent.mkdir(parents=True,exist_ok=True)
    E.indent(root);E.ElementTree(root).write(dest,encoding='UTF-8',xml_declaration=True)
    template=f'../models/{name}.sonx'
    base=f'add project id=adsb template="{template}"\n'
    base+='add output_file id=s11 path="$BASENAME.s1p" param=S file_format=TOUCH format=RI\n'
    base+=f'save path="../models/{name}_ready.sonx"\nverify_project\nget num_ports\n'
    (ROOT/f'macros/{name}_prepare.smc').write_text(base)
    (ROOT/f'macros/{name}_run.smc').write_text(base+'analyze\n')
    manifest={'variant':args.variant,'box_mm':args.box_mm,'requested_cell_mm':args.cell_mm,
        'actual_cell_mm':args.box_mm/nc,'air_each_side_mm':args.air_mm,'tan_delta':tand,
        'shift_from_kicad_mm':shift,'foil_midplane_separations_mm':intervals,
        'planar':counts,'barrels_including_plated_pads':via_count,'ports':selected,'solver_results':'NOT CALCULATED',
        'B_interpretation':'open RF barrel control, NOT an ideal zero-inductance connection'}
    (ROOT/f'models/{name}.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(dest)

if __name__=='__main__':main()
