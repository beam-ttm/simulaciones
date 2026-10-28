#!/usr/bin/env python3
"""Graph the measured solver point directly from Touchstone, outside SID cache."""
import copy
import math
import os
import xml.etree.ElementTree as E
import argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parents[2]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',type=Path,default=WORK/'sonnet/patch_simple.s1p')
    ap.add_argument('--out',type=Path,default=WORK/'sonnet/patch_simple_s11.sgrx')
    args=ap.parse_args()
    install=Path(os.environ.get('SONNET_DIR',str(Path.home()/'sonnet19')))
    template=install/'examples/wide_ring_coupler/wide_ring_coupler.sgrx'
    output=args.out.resolve()
    touchstone=args.data.resolve()
    if not touchstone.is_file() or not touchstone.stat().st_size:
        raise RuntimeError('Run patch_simple first: no Touchstone data')
    points=[]
    for line in touchstone.read_text().splitlines():
        line=line.split('!')[0].strip()
        if not line:continue
        if line.startswith('#'):
            if line.upper().split()[1:4]!=['GHZ','S','RI']:
                raise ValueError('Expected Sonnet one-port GHZ S RI data')
            continue
        f,re,im=map(float,line.split())
        points.append((f,20*math.log10(max(math.hypot(re,im),1e-300))))
    if not points:raise ValueError('No calculated data points')
    frequencies=[p[0] for p in points];values=[p[1] for p in points]
    single=len(set(frequencies))==1
    root=E.parse(template).getroot()
    windows=root.findall('Window')
    window=windows[0]
    for extra in windows[1:]:root.remove(extra)
    for tag in ['geometry','state']:
        el=window.find(tag)
        if el is not None:window.remove(el)
    graph=window.find('Guts/graph_info')
    graph.set('tab_label','Patch simple - S11')
    sources=graph.find('source_files');sources.clear()
    E.SubElement(E.SubElement(sources,'source',id='0'),'file').text=os.path.relpath(touchstone,output.parent)
    plots=graph.findall('plot');plot=plots[0]
    for extra in plots[1:]:graph.remove(extra)
    plot.set('graph_title','Patch simple - '+('un punto calculado a 1090 MHz' if single else 'S11 en frecuencias calculadas'))
    plot.find('graph_properties').set('show_symbols','1')
    plot.find('graph_units/frequency').set('unit','GHz')
    xmin,xmax=(frequencies[0]-.01,frequencies[0]+.01) if single else (min(frequencies),max(frequencies))
    ymin=-.2 if single else min(-5.,math.floor(min(values)/5)*5.)
    ymax=max(0.,math.ceil(max(values)/5)*5.)
    for name,lo,hi,title in [('x_axis',str(xmin),str(xmax),'Frequency (GHz)'),
                              ('y_axis_left',str(ymin),str(ymax),'S11 (dB)')]:
        axis=plot.find('axes/'+name)
        axis.set('min',lo);axis.set('max',hi);axis.set('autoscale','0')
        axis.set('enabled','1');axis.find('title').text=title
    plot.find('axes/y_axis_right').set('enabled','0')
    curves=plot.find('curves')
    curve=copy.deepcopy(curves.find('curve'));curves.clear();curves.append(curve)
    curve.set('id','1');curve.find('Format').set('value','0')
    ds=curve.find('Data_Source');ds.clear();ds.set('name','Data Source')
    E.SubElement(ds,'File',name='File',value='0')
    # External Touchstone is independent of de-embedded/non-de-embedded SID selection.
    curve.find('Ports/To_Port').set('value','1');curve.find('Ports/From_Port').set('value','1')
    curve.find('Style/Line_Style').set('value','1')
    markers=plot.find('markers')
    if markers is not None:markers.clear()
    E.indent(root);E.ElementTree(root).write(output,encoding='UTF-8',xml_declaration=True)
    print(output)

if __name__=='__main__':main()
