#!/usr/bin/env python3
"""Read one-port Touchstone, calculate metrics only from real solver output."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('touchstone',type=Path)
    ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'results')
    args=ap.parse_args()
    rows=[];unit='GHZ';fmt='MA';z0=50.
    for raw in args.touchstone.read_text().splitlines():
        s=raw.split('!')[0].strip()
        if not s:continue
        if s.startswith('#'):
            t=s.upper().split();unit=t[1]
            if t[2]!='S':raise ValueError('Only S-parameters supported')
            fmt=t[3];z0=float(t[t.index('R')+1]);continue
        if s.startswith('['):raise ValueError('Use Touchstone v1 one-port export')
        vals=[float(x) for x in s.split()]
        if len(vals)!=3:raise ValueError('Expected one-port Touchstone rows')
        f,a,b=vals
        gamma=complex(a,b) if fmt=='RI' else (10**(a/20) if fmt=='DB' else a)*np.exp(1j*np.deg2rad(b))
        rows.append((f*{'HZ':1,'KHZ':1e3,'MHZ':1e6,'GHZ':1e9}[unit],gamma))
    rows.sort();freq=np.array([r[0] for r in rows]);gamma=np.array([r[1] for r in rows])
    if not len(rows):raise ValueError('No solver frequency points')
    mag=abs(gamma)
    db=20*np.log10(np.maximum(mag,1e-300));vswr=np.where(mag<1,(1+mag)/(1-mag),np.nan)
    zin=z0*(1+gamma)/(1-gamma)
    args.out.mkdir(parents=True,exist_ok=True)
    with (args.out/(args.touchstone.stem+'.csv')).open('w') as f:
        w=csv.writer(f);w.writerow(['frequency_Hz','S11_real','S11_imag','S11_dB','return_loss_dB','VSWR','Zin_real_ohm','Zin_imag_ohm'])
        w.writerows(zip(freq,gamma.real,gamma.imag,db,-db,vswr,zin.real,zin.imag))
    idx=int(np.argmin(db));at=np.flatnonzero(np.isclose(freq,1.09e9,rtol=0,atol=1))
    report={'source':str(args.touchstone),'z0_ohm':z0,'minimum_S11_frequency_Hz':float(freq[idx]),
        'minimum_S11_dB':float(db[idx]),'note':'S11 minimum is a match minimum; inspect Zin/current modes before identifying resonance.',
        'at_1090MHz':None}
    if len(at):
        i=at[0];report['at_1090MHz']={'return_loss_dB':float(-db[i]),'VSWR':float(vswr[i]) if np.isfinite(vswr[i]) else None,
            'Zin_real_ohm':float(zin.real[i]),'Zin_imag_ohm':float(zin.imag[i])}
    (args.out/(args.touchstone.stem+'_metrics.json')).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    plt.plot(freq/1e6,db);plt.axvline(1090,color='gray',linestyle='--');plt.grid();plt.xlabel('Frecuencia [MHz]');plt.ylabel('S11 [dB]');plt.tight_layout()
    plt.savefig(args.out/(args.touchstone.stem+'_s11.png'),dpi=180)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
