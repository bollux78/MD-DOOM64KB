#!/usr/bin/env python3
"""R21 preflight: heap-model scenarios, source invariants and C predicate.
The CPU predicate test does not prove full-game frame equivalence.
"""
import importlib.util,json,pathlib,subprocess,sys,tempfile,os
r=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('heap',r/'scripts/lab/r21_heap_model.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
end=h.MEMORY_HIGH-5082
assert h.model(end)['boot']==3798
assert h.model(end,s5=True)['after']==2516
assert h.model(end,s5=True)['end_fail']
assert not h.model(end,s5=True,no_init=True)['end_fail']
assert h.model(end+2128)['boot_fail']
v=h.model(end,alloc=2128,no_init=True)
assert v['after']==1668 and not v['boot_fail'] and not v['end_fail']
m=json.loads((r/'scripts/lab/r21_matrix.json').read_text());assert len(m)==24
for n in m:assert len('doom-md-r21-'+n)<=30
for n in ['n3','n4','n3-n4','v2c','f1','f1-s5']:
 assert set(m['diag-'+n])==set(m[n])|{'R20_STACKGUARD','R21_STACK_PLAY'}
s=(r/'src/r_draw.c').read_text();start=s.index('boolean r21_need_tex =');end=s.index('R20_COUNT(R20C_SEGCOLS',start)
predicate=s[start:end].strip()
t=(r/'scripts/lab/test_r21_n4.c').read_text();start=t.index('boolean r21_need_tex =');end=t.index('return r21_need_tex;',start)
# Candidate really matches production, ignoring whitespace.
assert ''.join(predicate.split())==''.join(t[start:end].split()),'predicate test drift'
assert 'DMA_initEx(DMA_QUEUE_SIZE_MIN, (uint16_t)-1, DMA_BUFFER_SIZE_MIN)' in (r/'src/i_genesis.c').read_text()
with tempfile.TemporaryDirectory() as d:
 e=pathlib.Path(d)/'n4'
 subprocess.run([os.environ.get('CC','cc'),'-O2','-fsanitize=undefined','-fno-sanitize-recover=undefined',str(r/'scripts/lab/test_r21_n4.c'),'-o',str(e)],check=True)
 subprocess.run([str(e)],check=True)
print('PASS R21 heap scenarios, 24 variants/diagnostic pairs, exact N4 predicate with UBSan')
