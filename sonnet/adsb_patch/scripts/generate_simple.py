#!/usr/bin/env python3
"""Diagnostic two-conductor patch/ground model, separate from the real PCB."""
import copy
import json
import xml.etree.ElementTree as E
from pathlib import Path
from shapely.geometry import shape, Polygon
from generate_model import NS, node, set_project_header
from extract_geometry import ROOT, WORK

def main():
    q=lambda tag:'{'+NS+'}'+tag
    data=json.loads((ROOT/'geometry/extracted.json').read_text())
    patch=shape(next(z['outline'] for z in data['zones'] if z['layer']=='F.Cu'))
    ground=shape(next(z['outline'] for z in data['zones'] if z['layer']=='In1.Cu'))
    feed=next(v for v in data['vias'] if v['net']=='/1090_RF_IN')
    bounds=shape(data['outline']).bounds
    size,cell,air=1600.,.5,40.
    shift=(size/2-(bounds[0]+bounds[2])/2,size/2-(bounds[1]+bounds[3])/2)
    sourcecenter=tuple(round((v+s)/cell)*cell for v,s in zip(feed['at'],shift))
    stack=json.loads((ROOT/'stackup.json').read_text())
    cu=[v for v in stack['layers'] if v['Type']=='Copper']
    diel=next(v for v in stack['layers'] if v['Type']=='Dielectric')
    spacing=diel['Thickness']+(cu[0]['Thickness']+cu[1]['Thickness'])/2
    root=E.parse(ROOT/'source/blank.sonx').getroot()
    for tag in ['StartupGraphs']:
        el=root.find(q(tag))
        if el is not None:root.remove(el)
    set_project_header(root)
    root.find(q('Units')).find(q('Length')).text='MM'
    control=root.find(q('Control'));control.find(q('DeEmbed')).set('On','FALSE')
    node(control,'Currents',On='TRUE')
    geo=root.find(q('Geometry'));geo.clear();geo.set('YDirection','Negative')
    for mid,name,eps in [('air','Air',1),('substrate','Substrate',float(str(diel['DielectricConstant']).replace(',','.')))]:
        mat=node(geo,'Dielectric',MacroID=mid,Name=name,LossType='CONDUCTIVITY',Anisotropic='FALSE')
        node(mat,'FrequencyModel',ModelType='None',RefFreq=0,ValidRef='FALSE')
        for tag,val in [('Conductivity',0),('Eps',eps),('Tan',0),('MuRel',1),('MagLossTan',0)]:node(mat,tag,Value=val)
    node(geo,'Conductor',MacroID='copper',Name='Copper',Conductivity=5.8e7,LossType='CONDUCTIVITY')
    box=node(geo,'Box')
    for mid,typ in [('top_cover','TOP'),('bot_cover','BOTTOM')]:
        node(box,'BoxCover',MacroID=mid,Type=typ,MaterialType='FREE_SPACE',Roughness=0,Thickness=0)
    node(box,'Size',X=size,Y=size,Z=air*2+spacing)
    node(box,'NumCells',X=round(size/cell),Y=round(size/cell))
    node(box,'LocalOrigin',X=0,Y=size);node(box,'Symmetry',On='FALSE')
    for level,material,thickness,poly,cuthick in [(0,'Air',air,patch,cu[0]['Thickness']),
            (1,'Substrate',spacing,ground,cu[1]['Thickness']),(2,'Air',air,None,0)]:
        lev=node(geo,'Level',MacroID=f'lev{level}',MaterialName=material,Number=level)
        node(lev,'DielectricMaterialModel',Thickness=thickness)
        if poly is None:continue
        layer=node(node(lev,'Objects'),'PlanarTechLayer',MacroID=f'cu{level}',Name='Patch' if level==0 else 'GND',MaterialName='Copper')
        node(layer,'ColorPattern',Color='#b76e28' if level==0 else '#338899',Pattern='updiag')
        node(layer,'PlanarMaterialModel',CurrentRatio='.5',ModelType='THIN_METAL',Thickness=cuthick)
        node(layer,'RoughnessModel',RoughnessOn='FALSE')
        node(layer,'PlanarMeshing',EnableMesh='TRUE',FillType='RECTANGULAR')
        node(layer,'SubsectionMeshing',XMin=1,XMax=100,YMin=1,YMax=100,EdgeMeshed='TRUE',DiagonalEdges='FALSE',AnisotropicType='X_AND_Y')
        node(layer,'GLGMeshing',GLG='FALSE')
        p=node(node(layer,'Objects'),'PlanarPolygon',MacroID=f'p{level}',Id=level+1)
        node(p,'Points',' '.join(f'({x+shift[0]:.9f},{y+shift[1]:.9f})' for x,y in list(poly.exterior.coords)[:-1]))
    # Ideal voltage excitation between the two conductors, not a PCB barrel model.
    via=node(geo,'ViaTechLayer',MacroID='source_layer',Name='Ideal_excitation',MaterialName='Copper')
    node(via,'ColorPattern',Color='#bb44dd',Pattern='updiag')
    node(via,'ViaMaterialModel',ModelType='VOLUME',Solid='FALSE',Thickness=.025)
    node(via,'ViaMeshing',AutoHeight='FALSE',EnableMesh='TRUE',FillType='RING',HasPads='FALSE')
    node(via,'GLGMeshing',GLG='FALSE')
    node(via,'ViaLevels',FromLevel=0,FromType='LEVEL',ToLevel=1,ToType='LEVEL')
    x,y=sourcecenter
    coords=[(x-.5,y-.5),(x+.5,y-.5),(x+.5,y+.5),(x-.5,y+.5)]
    p=node(node(via,'Objects'),'ViaPolygon',MacroID='source',Id=3)
    node(p,'Points',' '.join(f'({a:.9f},{b:.9f})' for a,b in coords))
    port=node(node(p,'Objects'),'Port',MacroID='port1',Number=1,Vertex=0)
    node(port,'Type',Type='VIA')
    node(port,'Impedance',Resistance=50,Reactance=0,Inductance=0,Capacitance=0)
    node(port,'Center',f'({x:.9f},{y-.5:.9f})')
    sw=root.find(q('Sweeps'));sw.clear();sw.set('SweepVariables','FALSE')
    freqs=node(node(sw,'Set',MacroID='sweep',On='TRUE'),'Frequencies')
    node(freqs,'Sweep',MacroID='f1090',Type='STEP',On='TRUE',Adaptive='FALSE',Start='1.09')
    out=root.find(q('OutputFiles'));out.clear();out.set('Folder','.')
    name='patch_simple'
    E.indent(root);E.ElementTree(root).write(ROOT/f'models/{name}.sonx',encoding='UTF-8',xml_declaration=True)
    base=f'add project id=simple template="../models/{name}.sonx"\n'
    base+='add output_file id=s11 path="$BASENAME.s1p" param=S file_format=TOUCH format=RI\n'
    base+=f'save path="../models/{name}_ready.sonx"\nverify_project\nget num_ports\n'
    (ROOT/f'macros/{name}_prepare.smc').write_text(base)
    (ROOT/f'macros/{name}_remote_test.smc').write_text(base+'analyze server=10.16.100.159:56150\n')
    # Optional separate full-band project; the default is deliberately a single point.
    band=copy.deepcopy(root)
    fs=band.find('.//'+q('Frequencies'))
    node(fs,'Sweep',MacroID='band',Type='ABS_ENTRY',On='TRUE',Adaptive='TRUE',Start='.8',Stop='1.4',Target=300)
    E.indent(band);E.ElementTree(band).write(ROOT/'models/patch_simple_barrido.sonx',encoding='UTF-8',xml_declaration=True)
    baseband='add project id=simple template="../models/patch_simple_barrido.sonx"\n'
    baseband+='add output_file id=s11 path="$BASENAME.s1p" param=S file_format=TOUCH format=RI\n'
    baseband+='save path="../models/patch_simple_barrido_ready.sonx"\nverify_project\nget num_ports\n'
    (ROOT/'macros/patch_simple_barrido_prepare.smc').write_text(baseband)
    metadata={'purpose':'diagnostic simplified patch + finite GND, not the manufactured PCB',
        'patch_outline':list(patch.exterior.coords),'ground_outline':list(ground.exterior.coords),
        'source_reference_plane':'original In1.Cu plane treated as GND',
        'dielectric_gap_mm':diel['Thickness'],'copper_midplane_spacing_mm':spacing,
        'epsilon_r':float(str(diel['DielectricConstant']).replace(',','.')),'tan_delta':0,
        'box_mm':size,'cell_mm':cell,'cells_per_axis':int(size/cell),'air_each_side_mm':air,
        'source_type':'50 ohm via port; 1 mm square artificial source',
        'source_center_sonnet_mm':sourcecenter,'shift_from_kicad_mm':shift,
        'simplifications':['filled source clearance in patch','idealized GND from In1 zone outline',
            'removed copper layers In2 and B','removed all traces, components, pads, vias and mounting holes',
            'source is not the physical 0.3 mm PCB drill','lossless uniform dielectric; no masks or finite FR4 edges'],
        'single_point_GHz':1.09,'mesh_converged':False}
    (ROOT/'models/patch_simple.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('Generated diagnostic model: 2 planar polygons, 1 source, 3200 x 3200 cells')

if __name__=='__main__':main()
