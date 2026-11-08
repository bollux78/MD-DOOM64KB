#!/usr/bin/env python3
"""Independent test: exact sub camera applied to MD renderer with no MD ticker.
Raw frames stay private. This is camera-only replay with frozen local actors.
"""
import hashlib,json,os,struct,sys
from pathlib import Path
from r64a_rsp_capture import RSP,symbols
world='--world' in sys.argv
rom,elf=map(Path,[a for a in sys.argv[1:] if a!='--world']);syms=symbols(elf)
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
def decode_world(g):
    head=struct.unpack('>8I',g.readmem(0x600000,32))
    magic,version,count,nsec,nside,used,want,_=head
    assert (magic,version,count)==(0x53325742,1,27)
    assert 256<=used<=32768 and used%4==0
    raw=g.readmem(0x600000,used)
    h=2166136261
    for i,x in enumerate(raw):h=((h^(0 if 24<=i<28 else x))*16777619)&0xffffffff
    assert h==want,'world stream checksum'
    offsets=struct.unpack('>27I',raw[32:140]);sectors={};sides={};frames=[]
    changes=dict(height=0,light=0,flat=0,side=0)
    for frame,off in enumerate(offsets):
        tic,ns,nd,want,leveltime=struct.unpack_from('>IHHII',raw,off)
        assert tic==frame*100 and off>=256 and off%4==0
        p=off+16
        for j in range(ns):
            id,light,floor,ceil,fp,cp=struct.unpack_from('>Hh i i h h',raw,p);p+=16
            v=(floor,ceil,fp,cp,light);assert id<nsec
            if frame:
                old=sectors[id]
                changes['height']+=old[:2]!=v[:2];changes['light']+=old[4]!=light;changes['flat']+=old[2:4]!=v[2:4]
            sectors[id]=v
        for j in range(nd):
            id,*v,reserved=struct.unpack_from('>HhhhhH',raw,p);p+=12
            assert id<nside and reserved==0
            if frame:changes['side']+=sides[id]!=tuple(v)
            sides[id]=tuple(v)
        assert p==(offsets[frame+1] if frame<26 else used)
        assert len(sectors)==nsec and len(sides)==nside
        h=2166136261
        for x in [nsec,nside]+[v for i in range(nsec) for v in sectors[i]]+[v for i in range(nside) for v in sides[i]]:
            h=((h^(x&0xffffffff))*16777619)&0xffffffff
        assert h==want,('decoded world hash',frame,hex(h),hex(want))
        frames.append((want,ns,nd,leveltime))
    assert sum(changes.values())>0,'no world changes exercised'
    print('S2b decoded world',dict(bytes=used,sectors=nsec,sides=nside,changes=changes),flush=True)
    return frames,dict(bytes=used,sectors=nsec,sides=nside,changes=changes)
records=[]
world_frames=None;world_stats=None
try:
    for name in ('S2A_MDFrameDone','S2A_VisualDone','G_Ticker','P_Ticker','I_Error'):
        assert g.req('Z0,%x,2'%sym(name))=='OK'
    packets=None
    for _ in range(32):
        g.cont();pc=int(g.req('g')[17*8:18*8],16)&0xffffff
        if pc==sym('I_Error'):
            regs=g.req('g');sp=int(regs[15*8:16*8],16)&0xffffff
            ptr=int.from_bytes(g.readmem(sp+4,4),'big')&0xffffff
            msg=g.readmem(ptr,120).split(b'\0')[0].decode(errors='replace')
            raise RuntimeError('MD I_Error during sub-camera display: '+msg)
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
        if world and world_frames is None:world_frames,world_stats=decode_world(g)
        out=struct.unpack('>IIiiiIii',g.readmem(0x61b000,32))
        i=out[0];assert i==len(records)+1,('camera index',out)
        assert out[1:]==packets[i][1:],('applied MD camera differs from real sub packet',out,packets[i])
        if world:
            want,actual,ns,nd,leveltime=struct.unpack('>5I',g.readmem(0x61b020,20))
            assert (want,ns,nd,leveltime)==world_frames[i] and actual==want,('applied world',i,hex(actual),world_frames[i])
        fb=int.from_bytes(g.readmem(sym('r115_show'),4),'big')&0xffffff
        assert 0xff0000<=fb<0x1000000,hex(fb)
        pixels=g.readmem(fb,3344)
        (rom.parent/('camera-frame-%02d.bin'%i)).write_bytes(pixels)
        row=dict(index=i,tic=out[1],frame_sha256=hashlib.sha256(pixels).hexdigest(),camera=list(out[2:]))
        records.append(row)
        print('S2a rendered actual sub camera',i,'tic',out[1],row['frame_sha256'][:16],flush=True)
    assert len(records)==26,'incomplete visual replay'
    assert len({r['frame_sha256'] for r in records})>3,'rendered images did not change'
    assert g.req('M%x,1:01'%sym('s2a_test_exit'))=='OK'
    g.cont();pc=int(g.req('g')[17*8:18*8],16)&0xffffff
    assert pc==sym('G_Ticker'),'exit did not reach original MD title/game loop'
    report=dict(exit_to_md_loop=True,status='PASS' ,frames=26,md_logic_ticks=0,records=records,
                scope='Real sub-camera replay on MD renderer. Local actors/doors frozen; not full world offload or an FPS benchmark.')
    if world:
        report['world']=world_stats
        report['scope']='Real sub camera plus sector/side state applied to MD renderer; local actors frozen; offline replay.'
    (rom.parent/'visual_report.json').write_text(json.dumps(report,indent=2))
    if world:print('S2b WORLD PASS: 27 decoded snapshots; 26 applied world hashes match CD; no MD simulation ticks',flush=True)
    print('S2a VISUAL PASS: 26 frames; exact sub cameras; MD ticker absent during replay; exit to original MD loop PASS',flush=True)
finally:g.close()
