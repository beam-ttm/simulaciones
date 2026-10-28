#!/usr/bin/env python3
"""Create controlled comparisons and a mesh/box/cover convergence matrix."""
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

CASES = [
    ('A_real', []),
    ('B_no_rf_barrel', ['--variant','B_no_rf_barrel']),
    ('C_rf_wall_010', ['--variant','C_rf_wall_010']),
    ('C_rf_wall_035', ['--variant','C_rf_wall_035']),
    ('mesh_100um', ['--cell-mm','.1']),
    ('mesh_025um', ['--cell-mm','.025']),
    ('box_2000mm', ['--box-mm','2000']),
    ('box_2400mm', ['--box-mm','2400']),
    ('air_30mm', ['--air-mm','30']),
    ('air_50mm', ['--air-mm','50']),
    ('loss_assumed_016', ['--tan-delta','.016']),
]

if __name__=='__main__':
    for name,args in CASES:
        subprocess.run([sys.executable,str(ROOT/'scripts/generate_model.py'),'--name',name,*args],check=True)

