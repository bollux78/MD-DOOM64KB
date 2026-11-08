#!/usr/bin/env python3
"""Capture independent checkpoints from genuine MD G_Ticker, private CSV only."""
import csv, json, os, struct, sys
from pathlib import Path
from r64a_rsp_capture import RSP, symbols
rom,elf=map(Path,sys.argv[1:])
syms=symbols(elf)
def sym(name):
    matches=[v for k,v in syms.items() if k==name or k.startswith(name+'.')]
    assert len(matches)==1,(name,matches)
    return matches[0]&0xffffff
for attempt in range(3):
    g=RSP(os.environ['BLASTEM'],rom,16000,600)
    try:
        g.req('qSupported');break
    except (RuntimeError,BrokenPipeError):
        g.proc.wait(timeout=5)
        err=g.proc.stderr.read().decode(errors='replace');g.close()
        if 'out of range of a 32-bit displacement' not in err or attempt==2:
            print('BlastEm startup failed:',g.proc.returncode,err[-2000:],flush=True)
            raise
        print('Retrying BlastEm startup JIT allocation before execution',flush=True)
fields=('tic','player_x','player_y','player_z','angle','health','mobjs','prndindex')
rows=[];clocks=[]
try:
    for name in ('G_Ticker','S1E_MDCheckpoint','I_Error','R116_End'):
        assert g.req('Z0,%x,2'%sym(name))=='OK'
    armed=False
    for _ in range(100):
        g.cont();pc=int(g.req('g')[17*8:18*8],16)&0xffffff
        if pc==sym('I_Error'):raise RuntimeError('MD original engine I_Error')
        if pc==sym('R116_End'):raise RuntimeError('MD demo ended before 27 checkpoints')
        if pc==sym('G_Ticker'):
            assert not armed
            for name,value in (('r116_sel',1),('r116_norender',1),('r89_ai_low',0)):
                assert g.req('M%x,1:%02x'%(sym(name),value))=='OK'
            assert g.req('z0,%x,2'%sym('G_Ticker'))=='OK'
            armed=True
            continue
        assert pc==sym('S1E_MDCheckpoint'),hex(pc)
        assert g.readmem(sym('r116_active'),1)==b'\x01','wrong MD demo'
        raw=g.readmem(0x61c000,44)
        row=dict(zip(fields,struct.unpack('>IiiiIiII',raw[:32])))
        assert row['tic']==len(rows)*100,('missing/repeated MD checkpoint',row)
        rows.append(row);clocks.append(struct.unpack('>iii',raw[32:]))
        print('MD checkpoint',row,flush=True)
        if row['tic']==2600:break
    assert len(rows)==27,'incomplete MD trace'
    with (rom.parent/'md_trace.csv').open('w') as fp:
        w=csv.DictWriter(fp,fieldnames=fields);w.writeheader();w.writerows(rows)
    (rom.parent/'md_clock.json').write_text(json.dumps(clocks))
    print('MD original G_Ticker / 27 checkpoints PASS; last',rows[-1],flush=True)
    metadata=dict(initial_clock=clocks[0],final_clock=clocks[-1],
                  first_dead_tic=int.from_bytes(g.readmem(0x61c034,4),'big'),
                  deaths=int.from_bytes(g.readmem(sym('r116_res')+24,2),'big'))
    (rom.parent/'md_metadata.json').write_text(json.dumps(metadata))
    print('MD clock/death metadata',metadata,flush=True)
finally:g.close()
