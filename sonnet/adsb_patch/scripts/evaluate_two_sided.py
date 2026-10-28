#!/usr/bin/env python3
"""Export actual Sonnet fields and compare meshes; never synthesize EM data."""
import argparse, csv, json, math, os, re, signal, subprocess, time
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
# Use the 3D toolkit shipped with this Matplotlib, rather than the system namespace's older copy.
import mpl_toolkits
toolkit=Path(matplotlib.__file__).parent.parent/'mpl_toolkits'
if toolkit.is_dir():mpl_toolkits.__path__=[str(toolkit),*mpl_toolkits.__path__]
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parents[2]
SONNET=Path('/home/alan/sonnet19/bin/sonnet')

def read_fields(path):
    curves={};key=None
    for row in csv.reader(path.read_text().splitlines()):
        if len(row)!=2:continue
        if row[0].startswith('Theta'):
            m=re.search(r': (E-Total|E-RHP|E-LHP|Axial Ratio)\s+F=1\.09 GHz\s+Phi=([0-9]+)°',row[1])
            if not m:raise ValueError(f'Unexpected native field header: {row}')
            key=f'{m[1]}|{m[2]}'
            if key in curves:raise ValueError('Duplicate curve')
            curves[key]={};continue
        try:x,y=map(float,row)
        except ValueError:continue
        if key is None or not all(map(math.isfinite,[x,y])):raise ValueError('Invalid field sample')
        if x in curves[key]:raise ValueError('Duplicate angle')
        curves[key][x]=y
    if not curves or any(len(v)!=37 or 0. not in v for v in curves.values()):raise ValueError('Missing theta samples')
    return curves

def export_fields(case,out,sphere=False):
    dest=out/f'{case}_{"esfera" if sphere else "campo"}.csv';project=WORK/f'sonnet/{case}.sonx'
    expected=({f'E-Total|{p}' for p in range(0,360,5)} if sphere else
              {f'{m}|{p}' for m in ['E-Total','E-RHP','E-LHP','Axial Ratio'] for p in [0,90]})
    angles=set(range(0,181,5) if sphere else range(-90,91,5))
    if dest.exists():
        curves=read_fields(dest)
        if set(curves)==expected and all(set(v)==angles for v in curves.values()):return curves
    template='campo_esfera_1090.sptx' if sphere else 'campo_AR_1090.sptx'
    cmd=[str(SONNET),'-Additional','-farfield','-template',str(ROOT/'templates'/template),str(project),'-csv',str(dest)]
    with (out/f'{case}_field_export.log').open('w') as log:
        proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            until=time.monotonic()+180
            while time.monotonic()<until:
                if dest.exists():
                    try:
                        curves=read_fields(dest)
                        if set(curves)==expected and all(set(v)==angles for v in curves.values()) and str(project) in dest.read_text():return curves
                    except ValueError:pass
                if proc.poll() is not None and proc.returncode:raise RuntimeError('Native field export failed')
                time.sleep(.5)
            raise TimeoutError('Native field CSV not complete; inspect Sonnet GUI')
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)

def process(case,out):
    project=WORK/f'sonnet/{case}.sonx'
    logfile=ROOT/f'reports/{case}_solver.log'
    if not logfile.exists():logfile=ROOT/f'reports/{case}_remote.log'
    text=logfile.read_text()
    completed='Remote em simulation completed' in text or 'Local em simulation completed successfully.' in text
    if not completed or not re.search(r'Em errors detected:\s*0',text):raise RuntimeError(f'{case}: successful solver completion not confirmed')
    # Preserve the Windows originals before normalizing the SID line endings required by Linux's viewer.
    for sid in (WORK/f'sonnet/sondata/{case}').glob('*.sid'):
        data=sid.read_bytes()
        if b'\r\n' in data:
            backup=out/'windows_sid_backup'/case;backup.mkdir(parents=True,exist_ok=True)
            (backup/sid.name).write_bytes(data);fixed=data.replace(b'\r\n',b'\n');assert data.split()==fixed.split();sid.write_bytes(fixed)
    subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/postprocess_s11.py'),str(project.with_suffix('.s1p')),'--out',str(out)],check=True)
    with (out/f'{case}.csv').open() as f:rows=list(csv.DictReader(f))
    row=next(r for r in rows if abs(float(r['frequency_Hz'])-1.09e9)<1)
    s11={k:float(v) for k,v in row.items()};curves=export_fields(case,out)
    export_fields(case,out,sphere=True)
    ar={};v={}
    for phi in [0,90]:
        rh,lh=(10**(curves[f'{m}|{phi}'][0.]/20) for m in ['E-RHP','E-LHP'])
        ar[str(phi)]=20*math.log10((rh+lh)/abs(rh-lh)) if rh!=lh else None
        v[str(phi)]=(rh*rh-lh*lh)/(rh*rh+lh*lh)
    result={'case':case,'frequency_Hz':1.09e9,'S11':s11,'gain_boresight_dB':curves['E-Total|0'][0.],
            'maximum_gain_in_two_cuts_dB':max(max(curves[f'E-Total|{phi}'].values()) for phi in [0,90]),
            'AR_boresight_dB_from_circular_components':ar,'normalized_circular_imbalance':v,
            'native_AR_display_limit_dB':40,'native_field_csv':str((out/f'{case}_campo.csv').relative_to(WORK)),
            'native_sphere_csv':str((out/f'{case}_esfera.csv').relative_to(WORK))}
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for phi,col in [(0,'tab:red'),(90,'tab:blue')]:
        angles=list(curves[f'E-Total|{phi}'])
        axes[0].plot(angles,list(curves[f'E-Total|{phi}'].values()),color=col,label=f'Phi={phi}°')
        axes[1].plot(angles,list(curves[f'Axial Ratio|{phi}'].values()),color=col,label=f'Phi={phi}°')
    axes[0].set_ylabel('Power gain [dB]');axes[0].set_ylim(-40,5)
    axes[1].set_ylabel('Relación axial [dB], visor limitado a 40')
    axes[1].axhline(3,color='green',ls='--',label='3 dB')
    for ax in axes:ax.set_xlabel('Theta [°]');ax.grid(alpha=.3);ax.legend()
    fig.suptitle(f'{case}: 1090 MHz — datos exportados por Sonnet');fig.tight_layout();fig.savefig(out/f'{case}_campo.png',dpi=180);plt.close(fig)
    (out/f'{case}_metrics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result,curves

def compare(a,b,label):
    ra,ca=a;rb,cb=b
    ddb=abs(ra['S11']['S11_dB']-rb['S11']['S11_dB'])
    dg=abs(complex(ra['S11']['S11_real'],ra['S11']['S11_imag'])-complex(rb['S11']['S11_real'],rb['S11']['S11_imag']))
    dz=abs(complex(ra['S11']['Zin_real_ohm'],ra['S11']['Zin_imag_ohm'])-complex(rb['S11']['Zin_real_ohm'],rb['S11']['Zin_imag_ohm']))
    field_delta=max(abs(ca[f'E-Total|{p}'][t]-cb[f'E-Total|{p}'][t]) for p in [0,90] for t in ca[f'E-Total|{p}'] if abs(t)<=60)
    dv=max(abs(ra['normalized_circular_imbalance'][p]-rb['normalized_circular_imbalance'][p]) for p in ['0','90'])
    ar_delta=max((abs(ra['AR_boresight_dB_from_circular_components'][p]-rb['AR_boresight_dB_from_circular_components'][p]) for p in ['0','90'] if ra['AR_boresight_dB_from_circular_components'][p] is not None and rb['AR_boresight_dB_from_circular_components'][p] is not None), default=0.)
    low_ar=any(r['AR_boresight_dB_from_circular_components'][p] is not None and r['AR_boresight_dB_from_circular_components'][p]<10 for r in [ra,rb] for p in ['0','90'])
    sphere_delta=None
    if 'native_sphere_csv' in ra and 'native_sphere_csv' in rb:
        sa,sb=(read_fields(WORK/r['native_sphere_csv']) for r in [ra,rb])
        threshold=max(max(max(v.values()) for v in sa.values()),max(max(v.values()) for v in sb.values()))-20
        sphere_delta=max(abs(sa[k][t]-sb[k][t]) for k in sa for t in sa[k] if min(sa[k][t],sb[k][t])>=threshold)
    return {'comparison':label,'cases':[ra['case'],rb['case']],'delta_S11_dB':ddb,'delta_complex_gamma':dg,'delta_Zin_ohm':dz,'max_delta_gain_theta_pm60_two_cuts_dB':field_delta,'max_delta_gain_sphere_above_peak_minus_20dB':sphere_delta,'delta_normalized_circular_imbalance':dv,'delta_AR_boresight_dB':ar_delta,'within_selected_tolerances':ddb<=.1 and dg<=.005 and dz<=1 and field_delta<=.2 and dv<=.02 and (sphere_delta is None or sphere_delta<=.2) and (not low_ar or ar_delta<=.2),'scope':'1090 MHz only; power pattern above peak minus 20 dB, two phi cuts and polarization at theta=0. AR tolerance applied when either AR<10 dB; otherwise circular imbalance is used.'}

def sphere_plot(case,out):
    curves=export_fields(case,out,sphere=True)
    theta=np.radians(np.arange(0,181,5));phi=np.radians(np.arange(0,361,5))
    gain=np.array([[curves[f'E-Total|{p%360}'][float(t)] for t in range(0,181,5)] for p in range(0,361,5)])
    tt,pp=np.meshgrid(theta,phi);radius=10**((gain-gain.max())/20)
    x=radius*np.sin(tt)*np.cos(pp);y=radius*np.sin(tt)*np.sin(pp);z=radius*np.cos(tt)
    norm=matplotlib.colors.Normalize(vmin=max(float(gain.max())-30,-60),vmax=float(gain.max()))
    fig=plt.figure(figsize=(8,7));ax=fig.add_subplot(111,projection='3d')
    ax.plot_surface(x,y,z,facecolors=plt.cm.viridis(norm(gain)),rstride=1,cstride=1,shade=False)
    for setter in [ax.set_xlim,ax.set_ylim,ax.set_zlim]:setter(-1,1)
    ax.set_box_aspect((1,1,1));ax.set_xlabel('X');ax.set_ylabel('Y');ax.set_zlabel('Z')
    ax.set_title(f'Campo lejano a 1090 MHz\n{case}\nRadio: magnitud de campo normalizada; color: Power Gain',fontsize=10)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=ax,shrink=.65,label='Power Gain de Sonnet [dB]')
    fig.savefig(out/f'{case}_3D.png',dpi=180);plt.close(fig)
    ip,it=np.unravel_index(gain.argmax(),gain.shape)
    return {'sphere_samples':72*37,'maximum_gain_full_sphere_dB':float(gain.max()),'peak_theta_deg':int(it*5),'peak_phi_deg':int(ip*5)%360,'front_back_boresight_dB':float(gain[0,0]-gain[0,-1])}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('cases',nargs='+');ap.add_argument('--sphere',action='store_true');ap.add_argument('--pair',type=int,nargs=2,action='append');args=ap.parse_args()
    out=ROOT/'results/patch_2caras_h16';out.mkdir(parents=True,exist_ok=True)
    data=[process(c,out) for c in args.cases]
    pairs=args.pair if args.pair is not None else [(0,i) for i in range(1,len(data))]
    if any(i<0 or i>=len(data) for pair in pairs for i in pair):ap.error('Comparison index outside case list')
    report={'frequency_Hz':1.09e9,'metrics':[d[0] for d in data],'comparisons':[compare(data[i],data[j],f'{args.cases[i]}_vs_{args.cases[j]}') for i,j in pairs],'tolerances':{'S11_dB':.1,'complex_gamma':.005,'Zin_ohm':1,'gain_dB':.2,'circular_imbalance':.02,'AR_dB_when_below_10':.2},'limitations':['single frequency','infinite lateral dielectric slab','FR4 epsilon from CAD and loss tangent assumed','probe diameter assumed']}
    report['state']='comparisons_available' if report['comparisons'] else 'single_case_only'
    if args.sphere:report['sphere']=sphere_plot(args.cases[-1],out)
    (out/'convergencia.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
