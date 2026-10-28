#!/usr/bin/env python3
"""Two-sided antenna baseline from Altium PCB1; no receiver electronics."""
import copy
import argparse
import hashlib
import json
import math
import struct
import xml.etree.ElementTree as E
from pathlib import Path
import olefile
from shapely.geometry import Polygon
from generate_model import NS, node, set_project_header
from extract_geometry import ROOT, WORK

Q = lambda tag: '{' + NS + '}' + tag

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--box-mm',type=float,default=1228.8)
    ap.add_argument('--air-mm',type=float,default=40.)
    ap.add_argument('--cells',type=float,nargs='+',default=[.1,.075])
    ap.add_argument('--no-main',action='store_true')
    args=ap.parse_args()
    if args.box_mm<200 or args.air_mm<=.1 or any(c<=0 or abs(round(args.box_mm/c)*c-args.box_mm)>1e-6 for c in args.cells):
        ap.error('Invalid box/cell dimensions')
    source = WORK / 'PCB/2-Antena_patch/CubeSat_antenapatch/PCB1.PcbDoc'
    ole = olefile.OleFileIO(source)
    board = dict(v.split('=', 1) for v in ole.openstream('Board6/Data').read().decode('latin1').split('|') if '=' in v)
    mm = lambda value: float(value.removesuffix('mil')) * .0254
    cad_height = mm(board['V9_STACK_LAYER4_DIELHEIGHT'])
    height = 1.6  # User-specified FR4 dielectric thickness overrides Altium.
    copper = mm(board['V9_STACK_LAYER3_COPTHICK'])
    epsilon = float(board['V9_STACK_LAYER4_DIELCONST'])
    assert abs(cad_height-1.4)<1e-5 and abs(copper-.1)<1e-5 and epsilon==4.4
    data=ole.openstream('Polygons6/Data').read();offset=0;polys=[]
    while offset<len(data):
        length=struct.unpack_from('<I',data,offset)[0];offset+=4
        assert offset+length<=len(data)
        record=dict(v.split('=',1) for v in data[offset:offset+length].decode('latin1').strip('\0').split('|') if '=' in v)
        offset+=length
        points=[]
        for i in range(10000):
            if f'VX{i}' not in record:break
            points.append((mm(record[f'VX{i}']),-mm(record[f'VY{i}'])))
        if points:polys.append((record['LAYER'],Polygon(points)))
    patch=next(p for layer,p in polys if layer=='TOP' and 4000<p.area<4500)
    ground=next(p for layer,p in polys if layer=='BOTTOM' and p.area>5000)
    center=((patch.bounds[0]+patch.bounds[2])/2,(patch.bounds[1]+patch.bounds[3])/2)
    nominal=[(round(x-center[0],4),round(y-center[1],4)) for x,y in list(patch.exterior.coords)[:-1]]
    assert len(nominal)==6 and abs(Polygon(nominal).area-(66.5**2-.65**2))<1e-6
    assert all(abs((ground.bounds[i+2]-ground.bounds[i])-76)<.0001 for i in [0,1])
    # shortcut: probe diameter and FR4 loss are assumptions until hardware data are supplied.
    probe_diameter,tan_delta=.8,.02
    manifest={'source':str(source.relative_to(WORK)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'patch_vertices_relative_mm':nominal,'ground_mm':[76,76],'dielectric_gap_mm':height,
              'cad_dielectric_gap_mm':cad_height,'height_source':'explicit user override: 1.6 mm FR4',
              'epsilon_r':epsilon,'copper_mm':copper,'tan_delta_assumed':tan_delta,
              'probe_diameter_assumed_mm':probe_diameter,'feed_relative_mm':[0,19],
              'feed':'ideal 50-ohm via port, solid probe directly bonded to patch and finite GND; not the Altium pad/hole or connector',
              'limitations':['infinite uniform dielectric slab in Sonnet; finite substrate edges omitted',
                             'soldermask, coax connector and external cable omitted','FR4 loss assumed; epsilon from CAD, not measured'],
              'mesh_converged':False,'models':[]}
    for cell in args.cells:
        name=f'patch_2caras_h16_rect_b{args.box_mm:g}_c{round(cell*1000)}um'
        if args.air_mm!=40:name+=f'_a{args.air_mm:g}'
        root=E.parse(ROOT/'models/patch_simple.sonx').getroot();set_project_header(root)
        geo=root.find(Q('Geometry'));box=geo.find(Q('Box'));size=args.box_mm;air=args.air_mm
        geo.findall(Q('Level'))[0].find(Q('DielectricMaterialModel')).set('Thickness',str(air))
        geo.findall(Q('Level'))[2].find(Q('DielectricMaterialModel')).set('Thickness',str(air))
        box.find(Q('NumCells')).attrib.update(X=str(round(size/cell)),Y=str(round(size/cell)))
        box.find(Q('Size')).attrib.update(X=str(size),Y=str(size),Z=str(2*air+height))
        box.find(Q('LocalOrigin')).set('Y',str(size))
        material=geo.find(Q('Dielectric')+'[@Name="Substrate"]')
        material.find(Q('Eps')).set('Value',str(epsilon));material.find(Q('Tan')).set('Value',str(tan_delta))
        levels=geo.findall(Q('Level'))
        levels[1].find(Q('DielectricMaterialModel')).set('Thickness',str(height))
        for i,lev in enumerate(levels[:2]):
            tech=lev.find('.//'+Q('PlanarTechLayer'))
            metal=tech.find(Q('PlanarMaterialModel'));metal.attrib.clear()
            metal.attrib.update(ModelType='THICK_METAL',NumSheets='2',SheetsMode='AUTO_PLACEMENT',ThickDirection='UP' if i==0 else 'DOWN',Thickness=str(copper))
            # Far Field Viewer omits radiation from triangular subsections.
            tech.find(Q('SubsectionMeshing')).set('DiagonalEdges','FALSE')
            coords=nominal if i==0 else [(-38,-38),(38,-38),(38,38),(-38,38)]
            tech.find('.//'+Q('Points')).text=' '.join(f'({x+size/2:.6f},{y+size/2:.6f})' for x,y in coords)
        via=geo.find(Q('ViaTechLayer'));via.find(Q('ViaMaterialModel')).set('Solid','TRUE')
        vp=via.find('.//'+Q('ViaPolygon'));points=[(size/2+probe_diameter/2*math.cos(i*math.pi/32),size/2+19+probe_diameter/2*math.sin(i*math.pi/32)) for i in range(64)]
        vp.find(Q('Points')).text=' '.join(f'({x:.9f},{y:.9f})' for x,y in points)
        port=vp.find('.//'+Q('Port'));port.set('Vertex','0');port.find(Q('Center')).text=f'({size/2+.4},{size/2+19})'
        freqs=root.find('.//'+Q('Frequencies'));freqs.clear()
        node(freqs,'Sweep',MacroID='f1090',Type='STEP',On='TRUE',Adaptive='FALSE',Start='1.09')
        output=root.find(Q('OutputFiles'));output.clear();output.set('Folder','.')
        export=node(node(output,'Files'),'File',MacroID='s11',Type='TOUCH',Name='$BASENAME.s1p',UseInterpolatedData='TRUE',IncludeComments='TRUE',Precision=15,Parameter='S',Format='RI')
        node(node(export,'Terminations',Type='STD',Single='TRUE'),'Port',Rp=50,Xp=0,Lp=0,Cp=0)
        E.indent(root);dest=WORK/f'sonnet/{name}.sonx';E.ElementTree(root).write(dest,encoding='UTF-8',xml_declaration=True)
        macro=f'add project id=two template="{dest}"\nverify_project\nget num_ports\nsave path="{dest}"\n'
        (ROOT/f'macros/{name}_prepare.smc').write_text(macro)
        (ROOT/f'macros/{name}_run.smc').write_text(f'add project id=two template="{dest}"\nverify_project\nanalyze server=10.16.100.159:56150\n')
        assert len(root.findall('.//'+Q('PlanarPolygon')))==2
        assert len(geo.findall('.//'+Q('Port')))==1
        assert root.find(Q('Control')+'/'+Q('Currents')).get('On')=='TRUE'
        manifest['models'].append({'path':str(dest.relative_to(WORK)),'cell_mm':cell,'corner_cut_cells':.65/cell})
    band=copy.deepcopy(root)
    set_project_header(band)
    node(band.find('.//'+Q('Frequencies')),'Sweep',MacroID='band',Type='ABS_ENTRY',On='TRUE',Adaptive='TRUE',Start='.8',Stop='1.4',Target=300)
    E.indent(band)
    broad_sweep_valid=args.box_mm >= 4*299.792458/.8+76
    if not args.no_main:
        E.ElementTree(root).write(WORK/'sonnet/patch_2caras.sonx',encoding='UTF-8',xml_declaration=True)
        if broad_sweep_valid:
            E.ElementTree(band).write(WORK/'sonnet/patch_2caras_barrido.sonx',encoding='UTF-8',xml_declaration=True)
    manifest['point_project']=None if args.no_main else 'sonnet/patch_2caras.sonx'
    manifest['sweep_project']='sonnet/patch_2caras_barrido.sonx' if not args.no_main and broad_sweep_valid else None
    manifest['box_mm']=args.box_mm
    manifest['air_each_side_mm']=args.air_mm
    manifest['copper_model']='two-sheet thick metal; patch extends UP into air, GND DOWN into air; FR4 clear gap 1.6 mm'
    (ROOT/f'models/patch_2caras_h16_b{args.box_mm:g}_a{args.air_mm:g}.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
