#!/usr/bin/env python3
"""R85 combinations of the independently tested R84 changes, on R83 sprites."""
from pathlib import Path
import os
mode=os.environ['R85_CANDIDATE']
assert mode in ('control','sram','reuse','all')
s=Path('scripts/lab/apply_r84.py').read_text()
s=s.replace("mode=os.environ['R84_CANDIDATE'];assert mode in ('control','reuse','precomp','directory','sram')", "mode="+repr(mode))
s=s.replace("if mode=='reuse':", "if mode in ('reuse','all'):")
s=s.replace("if mode in ('precomp','directory'):", 'if True:')
s=s.replace("if mode=='precomp':", 'if True:')
s=s.replace("if mode=='sram':", "if mode in ('sram','all'):")
s=s.replace("'r84-'", "'r85-'")
exec(compile(s,'apply_r85-expanded.py','exec'))
