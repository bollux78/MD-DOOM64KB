#!/usr/bin/env python3
"""Independent test: exact sub camera applied to MD renderer with no MD ticker.
Raw frames stay private. This is camera-only replay with frozen local actors.
"""
import hashlib,json,os,struct,sys
from pathlib import Path
from r64a_rsp_capture import RSP,symbols
rom,elf=map(Path,sys.argv[1:]);syms=symbols(elf)
def sym(name):
    vals=[v for k,v in syms.items() if k==name or k.startswith(name+'.')]
    assert len(vals)==1,(name,vals)
    return vals[0]&0xffffff
for attempt in range(3):
    g=RSP(os.environ['BLASTEM'],rom,16000,600)
    try:g.req('qSupported');break
    except (RuntimeError,BrokenPipeError):
        g.proc.wait(timeout=5);err=g.proc.stderr.read().decode(errors='replace');g.close()
        if 'out of range of a 32-bit displacement' not in err or attempt==2:raise
        print('Retrying startup JIT allocation before ROM execution',flush=True)
records=[]
try:
    for name in ('S2A_MDFrameDone','S2A_VisualDone','G_Ticker','P_Ticker','I_Error'):
        assert g.req('Z0,%x,2'%sym(name))=='OK'
    packets=None
    for _ in range(32):
        g.cont();pc=int(g.req('g')[17*8:18*8],16)&0xffffff
        if pc==sym('I_Error'):raise RuntimeError('MD I_Error during sub-camera display')
        if pc in (sym('G_Ticker'),sym('P_Ticker')):raise RuntimeError('MD simulation ticked during camera-only proof')
        if pc==sym('S2A_VisualDone'):break
        assert pc==sym('S2A_MDFrameDone'),hex(pc)
        if packets is None:
            raw=g.readmem(0x61a000,864)
            packets=[struct.unpack('>IIiiiIii',raw[i*32:(i+1)*32]) for i in range(27)]
            magic,count,stride,want=struct.unpack('>4I',g.readmem(0x61a380,16))
            h=2166136261
            for x in struct.unpack('>216I',raw):h=((h^x)*16777619)&0xffffffff
            assert (magic,count,stride)==(0x53324142,27,32) and h==want,'camera transport hash'
            assert all(p[0]==0x53324341 and p[1]==i*100 for i,p in enumerate(packets))
        out=struct.unpack('>IIiiiIii',g.readmem(0x61b000,32))
        i=out[0];assert i==len(records)+1,('camera index',out)
        assert out[1:]==packets[i][1:],('applied MD camera differs from real sub packet',out,packets[i])
        fb=int.from_bytes(g.readmem(sym('r115_show'),4),'big')&0xffffff
        assert 0xff0000<=fb<0x1000000,hex(fb)
        pixels=g.readmem(fb,3344)
        (rom.parent/('camera-frame-%02d.bin'%i)).write_bytes(pixels)
        row=dict(index=i,tic=out[1],frame_sha256=hashlib.sha256(pixels).hexdigest(),camera=list(out[2:]))
        records.append(row)
        print('S2a rendered actual sub camera',i,'tic',out[1],row['frame_sha256'][:16],flush=True)
    assert len(records)==26,'incomplete visual replay'
    assert len({r['frame_sha256'] for r in records})>3,'rendered images did not change'
    report=dict(status='PASS',frames=26,md_logic_ticks=0,records=records,
                scope='Real sub-camera replay on MD renderer. Local actors/doors frozen; not full world offload or an FPS benchmark.')
    (rom.parent/'visual_report.json').write_text(json.dumps(report,indent=2))
    print('S2a VISUAL PASS: 26 frames; exact sub cameras; MD G_Ticker never executed',flush=True)
finally:g.close()
