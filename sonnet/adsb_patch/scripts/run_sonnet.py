#!/usr/bin/env python3
"""Run validated macros, retaining logs and explicit solver status."""
import argparse
import json
import os
import re
import signal
import shutil
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('case',nargs='?',default='A_real')
    ap.add_argument('--analyze',action='store_true')
    ap.add_argument('--timeout',type=int,default=180)
    args=ap.parse_args()
    executable=shutil.which('runmacro')
    if not executable:ap.error('runmacro not on PATH')
    macro=ROOT/'macros'/f'{args.case}_{"run" if args.analyze else "prepare"}.smc'
    if not macro.is_file():ap.error(f'Missing macro: {macro}')
    log=ROOT/'reports'/f'{args.case}_{"analysis" if args.analyze else "prepare"}.log'
    status={'case':args.case,'analysis_requested':args.analyze,'complete':False}
    started=time.time()
    try:
        with log.open('w') as f:
            process=subprocess.Popen([executable,'-v',macro.name],cwd=macro.parent,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                returncode=process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait()
                raise
        output=log.read_text()
        status.update(returncode=returncode,verify_passed='Verify passed' in output)
        status['one_port_confirmed']=bool(re.search(r'"Ports"\s*:\s*1\s*}',output))
        status['complete']=returncode==0 and status['verify_passed'] and status['one_port_confirmed'] and not re.search(r'(?i)(sonnet error|licensing error|analysis failed|verify failed)',output)
        if args.analyze:
            candidates=[ROOT/f'models/{args.case}_ready.s1p',ROOT/f'models/{args.case}.s1p']
            status['touchstone']=[str(p.relative_to(ROOT)) for p in candidates if p.is_file() and p.stat().st_mtime>=started]
            status['complete'] &= bool(status['touchstone'])
    except subprocess.TimeoutExpired:
        status['failure']='timeout; simulation has not completed'
    (log.with_suffix('.json')).write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status,indent=2))
    if not status['complete']:raise SystemExit(1)

if __name__=='__main__':main()

