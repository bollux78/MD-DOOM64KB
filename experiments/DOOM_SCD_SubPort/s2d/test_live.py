#!/usr/bin/env python3
"""Interactive dual-CPU proof: controller -> CD G_Ticker -> MD native renderer.
No MD simulation ticks permitted before requested exit. All files private.
"""
import hashlib,json,os,struct,sys
from pathlib import Path
from r64a_rsp_capture import RSP,symbols
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'s2c'))
from test_actors import check_applied,mix
rom,elf=map(Path,sys.argv[1:]);syms=symbols(elf)
def sym(n):
    v=[v for k,v in syms.items() if k==n or k.startswith(n+'.')];assert len(v)==1,(n,v)
    return v[0]&0xffffff
for attempt in range(3):
    g=RSP(os.environ['BLASTEM'],rom,16000,600)
    try:g.req('qSupported');break
    except (RuntimeError,BrokenPipeError):
        g.proc.wait(timeout=5);err=g.proc.stderr.read().decode(errors='replace');g.close()
        if 'out of range of a 32-bit displacement' not in err or attempt==2:raise
rows=[];commands={};stopping=False

def command(tic,joy,stop=0):
    f=(50 if joy&32 else 25) if joy&1 else (-50 if joy&32 else -25) if joy&2 else 0
    side=(-24 if joy&4 else 24 if joy&8 else 0) if joy&32 else 0
    turn=0 if joy&32 else 640 if joy&4 else -640 if joy&8 else 0
    return struct.pack('>IIbbhHH',0x53324449,tic,f,side,turn,(2 if joy&64 else 0)|(1 if joy&16 else 0),stop)

def decode(g):
    header=g.readmem(0x61a000,256);magic,version,tic,total,wb,ab,status,want=struct.unpack_from('>8I',header)
    assert (magic,version,status)==(0x53324446,1,0) and total==256+wb+ab and total<=16384
    world=g.readmem(0x600000,wb);actors=g.readmem(0x608000,ab)
    raw=bytearray(header+world+actors);raw[28:32]=bytes(4);h=2166136261
    for x in raw:h=mix(h,x)
    assert h==want,'live frame transport checksum'
    wm,wv,wc,ns,nd,used,whash,_=struct.unpack_from('>8I',world)
    assert (wm,wv,wc,used)==(0x53325742,1,1,wb)
    off=struct.unpack_from('>I',world,32)[0];zero,nsec,nside,want,leveltime=struct.unpack_from('>IHHII',world,off)
    assert not zero and (nsec,nside)==(ns,nd)
    p=off+16;vals=[]
    for i in range(ns):
        id,light,floor,ceil,fp,cp=struct.unpack_from('>Hhiihh',world,p);p+=16;assert id==i
        vals += [floor,ceil,fp,cp,light]
    for i in range(nd):
        id,offset,top,bottom,mid,res=struct.unpack_from('>HhhhhH',world,p);p+=12;assert id==i and not res
        vals += [offset,top,bottom,mid]
    assert p==wb;h=mix(mix(2166136261,ns),nd)
    for x in vals:h=mix(h,x)
    assert h==want
    wwant,actual,ans,and_,alevel=struct.unpack('>5I',g.readmem(0x61b020,20))
    assert (wwant,actual,ans,and_,alevel)==(want,want,ns,nd,leveltime)
    am,av,ac,nrom,used,ahash,stride,res=struct.unpack_from('>8I',actors)
    assert (am,av,ac,used,stride,res)==(0x53324342,1,1,ab,36,0)
    off=struct.unpack_from('>I',actors,32)[0];zero,n,nr,want,player,res=struct.unpack_from('>IHHIHH',actors,off)
    assert zero==0 and nr==nrom and not res
    p=off+16;records=[]
    for _ in range(n):records.append(struct.unpack_from('>HHiiiIIHHHhhH',actors,p));p+=36
    actor_bytes=actors[off+16:p];rvals=[]
    for i in range(nrom):
        id,dead,delay,res=struct.unpack_from('>4H',actors,p);p+=8;assert id==i and dead in (0,1) and not res
        rvals += [dead,delay]
    assert p==ab;h=2166136261
    for x in [n,nrom,player]+[x for r in records for x in r]+rvals:h=mix(h,x)
    assert h==want
    check_applied(g,tic,dict(hash=want,n=n,nr=nr,player=player,records=records,actor_bytes=actor_bytes),sym)
    out=struct.unpack('>7I',g.readmem(0x61b000,28));camera=struct.unpack_from('>8I',header,32)
    assert out[:6]==(tic,camera[2],camera[3],camera[5],camera[7],struct.unpack_from('>I',header,72)[0])
    audit=struct.unpack('>10I',g.readmem(0x61b100,40))
    assert audit[:2]==struct.unpack_from('>2I',header,88)
    assert audit[2:]==struct.unpack_from('>8I',header,160),'native weapon/flash psprites differ from CD'
    return header,dict(tic=tic,x=out[1],y=out[2],angle=out[3],health=out[4],ammo=out[5],bank=out[6],world_bytes=wb,actor_bytes=ab,actors=n)
commands[0]=command(0,0)
try:
    for name in ('s1b_complete','S2D_MDFrameDone','G_Ticker','P_Ticker','I_Error'):
        assert g.req('Z0,%x,2'%sym(name))=='OK'
    for _ in range(105):
        g.cont();pc=int(g.req('g')[136:144],16)&0xffffff
        if pc==sym('I_Error'):
            regs=g.req('g');sp=int(regs[120:128],16)&0xffffff;ptr=int.from_bytes(g.readmem(sp+4,4),'big')&0xffffff
            raise RuntimeError('MD I_Error: '+g.readmem(ptr,120).split(b'\0')[0].decode(errors='replace'))
        if pc==sym('s1b_complete'):
            stage,served,errors,marker,*_=struct.unpack('>4H4I',g.readmem(0x61f000,24))
            assert (stage,served,errors,marker)==(5,18,0,0x5a9d)
            assert g.req('z0,%x,2'%pc)=='OK';continue
        if pc in (sym('G_Ticker'),sym('P_Ticker')):
            assert stopping and pc==sym('G_Ticker'),'MD simulation ticked during live CD play'
            assert int.from_bytes(g.readmem(0x61b0a0,4),'big')==1,'exit did not restore local state'
            break
        assert pc==sym('S2D_MDFrameDone'),hex(pc)
        header,row=decode(g);tic=row['tic'];assert tic==len(rows)
        if tic:assert header[192:208]==commands[tic-1],('input echo',tic,header[192:208].hex(),commands[tic-1].hex())
        if tic:
            fb=int.from_bytes(g.readmem(sym('r115_show'),4),'big')&0xffffff
            pixels=g.readmem(fb,3344);row['frame_sha256']=hashlib.sha256(pixels).hexdigest()
            if tic in (1,16,32,64,96):(rom.parent/('live-frame-%03d.bin'%tic)).write_bytes(pixels)
        rows.append(row)
        if tic>=96:
            stopping=True;assert g.req('M%x,1:01'%sym('s2d_test_exit'))=='OK'
            joy=0
        else:joy=1 if tic<16 else 4 if tic<32 else (16|64 if tic>=80 else 16)
        assert g.req('M%x,2:%04x'%(sym('s2d_test_buttons'),joy))=='OK'
        commands[tic+1]=command(tic+1,joy,int(stopping))
        print('S2d live applied',tic,'actors',row['actors'],'ammo',row['ammo'],'bank',row['bank'],flush=True)
    else:raise AssertionError('missing normal exit')
    assert len(rows)>=97 and len({(r['x'],r['y']) for r in rows})>8
    assert len({r['angle'] for r in rows})>8 and min(r['ammo'] for r in rows)<rows[0]['ammo']
    assert {r['bank'] for r in rows}=={4,5},'Word RAM banks did not alternate'
    assert len({r.get('frame_sha256') for r in rows})>8
    report=dict(status='PASS',frames=len(rows),md_simulation_ticks=0,controller_echo=True,exit_restored=True,rows=rows,
                scope='One real CD tic per exchange with live MD inputs and native MD renderer. E1M1 prototype; full snapshots; no FPS/35Hz claim.')
    (rom.parent/'live_report.json').write_text(json.dumps(report,indent=2))
    print('S2d LIVE PASS: actual movement/turn/fire, input echo, 2 Word RAM banks, exact world/actors, no MD logic, exit restored',flush=True)
finally:g.close()
