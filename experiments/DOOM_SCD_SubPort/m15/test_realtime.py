#!/usr/bin/env python3
"""Interactive dual-CPU proof: controller -> CD G_Ticker -> MD native renderer.
No MD simulation ticks permitted before requested exit. All files private.
"""
import hashlib,json,os,struct,sys,math
from pathlib import Path
from r64a_rsp_capture import RSP,symbols
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'s2c'))
from check_actors import check_applied
def mix(h,x):return (((((h<<5)|(h>>27))&0xffffffff)^(x&0xffffffff))+0x9e3779b9)&0xffffffff
fast=True
production='--production' in sys.argv
route='--route' in sys.argv
nav_phase=0;nav_neutral=False;nav_finish=0;door_open=False;door_started=False;occluded_retained=False
waypoints=[(1312,-3520),(1248,-3400),(1280,-3100),(1280,-2848),(1320,-2600),(1472,-2496),(1632,-2496)]
assert not production or fast
rom,elf=map(Path,[a for a in sys.argv[1:] if a not in ('--fast','--production','--route')]);syms=symbols(elf)
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

world_sectors={};world_sides={};rom_states={};known_types={}
def word_checksum(raw):
    assert len(raw)%4==0
    h=2166136261
    for i,x in enumerate(struct.unpack('>%dI'%(len(raw)//4),raw)):
        h=((h<<5)|(h>>27))&0xffffffff;h^=0 if i==7 else x;h=(h+0x9e3779b9)&0xffffffff
    return h

def decode(g):
    header=g.readmem(0x61a000,256);magic,version,tic,total,wb,ab,status,want=struct.unpack_from('>8I',header)
    assert (magic,version,status)==(0x53324d35,3,0) and total==256+wb+ab and total<=16384
    world=g.readmem(0x601100,wb);actors=g.readmem(0x601100+wb,ab)
    def words(raw):
        h=2166136261
        for v in struct.unpack('>%dI'%(len(raw)//4),raw):h=mix(h,v)
        return h
    assert words(header[:252])==struct.unpack_from('>I',header,252)[0],'mutable header checksum'
    assert words(world+actors)==want,'immutable snapshot checksum'
    wm,wv,wc,ns,nd,used,whash,_=struct.unpack_from('>8I',world)
    assert (wm,wv,wc,used)==(0x53325742,2,1,wb)
    if fast:assert whash==0
    off=struct.unpack_from('>I',world,32)[0];zero,nsec,nside,want,leveltime=struct.unpack_from('>IHHII',world,off)
    assert not zero and nsec<=ns and nside<=nd
    if not fast or not tic:assert (nsec,nside)==(ns,nd)
    p=off+16;seen=set()
    for i in range(nsec):
        id,light,floor,ceil,fp,cp=struct.unpack_from('>Hhiihh',world,p);p+=16
        assert id<ns and id not in seen;seen.add(id);world_sectors[id]=[floor,ceil,fp,cp,light]
    seen=set()
    for i in range(nside):
        id,offset,top,bottom,mid,res=struct.unpack_from('>HhhhhH',world,p);p+=12
        assert id<nd and id not in seen and not res;seen.add(id);world_sides[id]=[offset,top,bottom,mid]
    assert p==wb and len(world_sectors)==ns and len(world_sides)==nd
    h=mix(mix(2166136261,ns),nd)
    for i in range(ns):
        f=mix(2166136261,i)
        for x in world_sectors[i]:f=mix(f,x)
        h^=f
    for i in range(nd):
        f=mix(2166136261,0x80000000|i)
        for x in world_sides[i]:f=mix(f,x)
        h^=f
    assert h==want
    checked=not production or tic%32==0
    wwant,actual,ans,and_,alevel,wchecked=struct.unpack('>6I',g.readmem(0x61b020,24))
    assert wchecked==int(checked)
    assert (wwant,actual,ans,and_,alevel)==(want,want if checked else 0,nsec,nside,leveltime)
    am,av,ac,nrom,used,ahash,stride,res=struct.unpack_from('>8I',actors)
    assert (am,av,ac,used,stride)==(0x53324342,2,1,ab,24) and 0<res<=64
    if fast:assert ahash==0
    off=struct.unpack_from('>I',actors,32)[0];zero,n,nr,want,player,res=struct.unpack_from('>IHHIHH',actors,off)
    assert zero==0 and nr<=nrom and not res
    if not fast or not tic:assert nr==nrom
    p=off+16;records=[]
    for _ in range(n):records.append(struct.unpack_from('>HHiiiBBHHH',actors,p));p+=24
    actor_bytes=actors[off+16:p];seen=set()
    for v in records:
        assert v[0] not in known_types or known_types[v[0]]==v[1],'stable actor ID changed type'
        known_types[v[0]]=v[1]
        if v[0]!=player:
            x,y=struct.unpack_from('>ii',header,40)
            assert abs(v[2]-x)<=1280*65536 and abs(v[3]-y)<=1280*65536,'actor relevance bound'

    for i in range(nr):
        id,dead,delay,res=struct.unpack_from('>4H',actors,p);p+=8
        assert id<nrom and id not in seen and dead in (0,1) and not res
        seen.add(id);rom_states[id]=[dead,delay]
    assert p==ab and len(rom_states)==nrom;h=2166136261
    for x in [n,nrom,player]+[x for r in records for x in r]+[x for i in range(nrom) for x in rom_states[i]]:h=mix(h,x)
    assert h==want
    global occluded_retained
    if route and world_sectors[4][1]==0:
        occluded_retained |= any(v[1]==2 and v[2]>1550*65536 and v[3]>-3000*65536 for v in records)
    check_applied(g,tic,dict(hash=want,n=n,nr=nr,player=player,records=records,actor_bytes=actor_bytes),sym,checked=checked)
    assert int.from_bytes(g.readmem(0x61b070,4),'big')==int(checked)
    out=struct.unpack('>7I',g.readmem(0x61b000,28));camera=struct.unpack_from('>8I',header,32)
    assert out[:6]==(tic,camera[2],camera[3],camera[5],camera[7],struct.unpack_from('>I',header,72)[0])
    audit=struct.unpack('>10I',g.readmem(0x61b100,40))
    assert audit[:2]==struct.unpack_from('>2I',header,88)
    assert audit[2:]==struct.unpack_from('>8I',header,160),'native weapon/flash psprites differ from CD'
    return header,dict(tic=tic,x=out[1],y=out[2],angle=out[3],health=out[4],ammo=out[5],bank=out[6],world_bytes=wb,actor_bytes=ab,actors=n,capture_world_units=struct.unpack_from('>I',actors,36)[0],capture_actor_units=struct.unpack_from('>I',actors,40)[0],item_count=struct.unpack_from('>I',header,140)[0],door_ceiling=world_sectors[4][1],changed_sectors=nsec,changed_sides=nside,changed_rom=nr,checked=checked,profile_vblanks=list(struct.unpack('>6I',g.readmem(0x61b140,24))))
commands[0]=command(0,0)
try:
    for name in ('s1b_complete','S2D_MDFrameDone','G_Ticker','P_Ticker','I_Error'):
        assert g.req('Z0,%x,2'%sym(name))=='OK'
    for _ in range(205 if route else 105):
        g.cont();pc=int(g.req('g')[136:144],16)&0xffffff
        if pc==sym('I_Error'):
            regs=g.req('g');sp=int(regs[120:128],16)&0xffffff;ptr=int.from_bytes(g.readmem(sp+4,4),'big')&0xffffff
            raise RuntimeError('MD I_Error: '+g.readmem(ptr,120).split(b'\0')[0].decode(errors='replace'))
        if pc==sym('s1b_complete'):
            stage,served,errors,marker,*_=struct.unpack('>4H4I',g.readmem(0x61f000,24))
            assert (stage,served,errors,marker)==(5,18,0,0x5abd)
            if fast:assert g.req('M%x,1:%02x'%(sym('s2e_test_deep'),0 if production else 1))=='OK'
            print('M15 boot ready',flush=True)
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
        metrics=struct.unpack_from('>9I',header,208)
        raster,conversion,vblank=struct.unpack('>3I',g.readmem(0x61b180,12))
        row.update(capture_hash_units=metrics[7],capture_copy_units=metrics[8],game_tic=metrics[0],clock_units=metrics[1],dropped=metrics[2],tick_count=metrics[3],tick_cost_total=metrics[4],tick_cost_max=metrics[5],max_poll=metrics[6],vblank=vblank,raster_stopwatch_units=raster,conversion_stopwatch_units=conversion)
        wait,copied,world_cost,actors_cost,total,proxy,player_cost=struct.unpack('>7I',g.readmem(0x61b280,28))
        capmax,period,age=struct.unpack_from('>3I',header,148)
        captures,capture_total=struct.unpack_from('>2I',header,244)
        row.update(proxy_units=proxy,player_units=player_cost,demand_units=wait,copy_units=copied,apply_world_units=world_cost,apply_actors_units=actors_cost,total_units=total,captures=captures,capture_total_units=capture_total,capture_max_units=capmax,capture_period=period,snapshot_age=age)
        rows.append(row)
        if route:
            door_started |= row['door_ceiling']>0
            door_open |= row['door_ceiling']>=32*65536
            x=row['x'] if row['x']<2**31 else row['x']-2**32
            y=row['y'] if row['y']<2**31 else row['y']-2**32
            x/=65536;y/=65536
            if nav_phase<len(waypoints):
                wx,wy=waypoints[nav_phase];distance=math.hypot(wx-x,wy-y)
                if (nav_phase==0 and row['item_count']>rows[0]['item_count']) or (nav_phase>0 and distance<56):nav_phase+=1
            if nav_phase==len(waypoints):
                nav_finish+=1;joy=(8|16) if nav_finish<=3 else 16
            elif nav_neutral:
                joy=0;nav_neutral=False
            else:
                wx,wy=waypoints[nav_phase]
                target=math.atan2(wy-y,wx-x);angle=row['angle']*2*math.pi/2**32
                diff=(target-angle+math.pi)%(2*math.pi)-math.pi
                joy=(4 if diff>0 else 8) if abs(diff)>math.radians(18) else 1
                nav_neutral=True
            if nav_phase>=5 and (door_started or tic%8==0):joy|=64
            if tic<2:joy|=16
            print('M15 route',tic,'phase',nav_phase,'xy',round(x,1),round(y,1),'item',row['item_count'],'door',round(row['door_ceiling']/65536),flush=True)
            if nav_finish>=6 or tic>=190:
                stopping=True;joy=0;assert g.req('M%x,1:01'%sym('s2d_test_exit'))=='OK'
        elif tic>=48:
            stopping=True;assert g.req('M%x,1:01'%sym('s2d_test_exit'))=='OK';joy=0
        else:joy=(1|16) if tic<8 else (4|16) if tic<16 else (16|64 if tic>=40 else 16)
        assert g.req('M%x,2:%04x'%(sym('s2d_test_buttons'),joy))=='OK'
        commands[tic+1]=command(tic+1,joy,int(stopping))
        print('S2d live applied',tic,'actors',row['actors'],'ammo',row['ammo'],'bank',row['bank'],flush=True)
    else:raise AssertionError('missing normal exit')
    assert len(rows)>=(20 if route else 49) and len({(r['x'],r['y']) for r in rows})>2
    assert len({r['angle'] for r in rows})>2 and min(r['ammo'] for r in rows)<rows[0]['ammo']
    assert {r['bank'] for r in rows}=={4,5},'Word RAM banks did not alternate'
    assert len({r.get('frame_sha256') for r in rows})>8
    if fast:
        assert max(r['world_bytes'] for r in rows[1:])<rows[0]['world_bytes']//2,'world deltas not exercised'
        assert any(r['changed_rom']==0 for r in rows[1:]),'R24 deltas not exercised'
    a,b=rows[8],rows[-2]
    hz=(b['game_tic']-a['game_tic'])*60/(b['vblank']-a['vblank'])
    print('M1 independent MD-clock logic Hz',hz,'dropped',b['dropped'],flush=True)
    print('M1 telemetry',json.dumps(dict(presentation_fps=(b['tic']-a['tic'])*60/(b['vblank']-a['vblank']),game_tics=b['game_tic'],elapsed_units=b['clock_units'],tick_count=b['tick_count'],mean_tick_ms=b['tick_cost_total']*0.03072/max(1,b['tick_count']),max_tick_ms=b['tick_cost_max']*0.03072,max_poll_ms=b['max_poll']*0.03072,first_drop_frame=next((r['tic'] for r in rows if r['dropped']),None))),flush=True)
    steady=rows[8:-1]
    fps=(b['tic']-a['tic'])*60/(b['vblank']-a['vblank'])
    telemetry=dict(presentation_fps=fps,demand_mean_ms=sum(r['demand_units'] for r in steady)*0.03072/len(steady),demand_max_ms=max(r['demand_units'] for r in steady)*0.03072,apply_world_ms=sum(r['apply_world_units'] for r in steady)*0.03072/len(steady),apply_actors_ms=sum(r['apply_actors_units'] for r in steady)*0.03072/len(steady),capture_mean_ms=b['capture_total_units']*0.03072/max(1,b['captures']),capture_max_ms=b['capture_max_units']*0.03072,mean_tick_ms=b['tick_cost_total']*0.03072/max(1,b['tick_count']),max_snapshot_age=max(r['snapshot_age'] for r in rows),max_poll_ms=b['max_poll']*0.03072)
    telemetry.update(raster_ms=sum(r['raster_stopwatch_units'] for r in steady)*0.03072/len(steady),proxy_ms=sum(r['proxy_units'] for r in steady)*0.03072/len(steady),player_ms=sum(r['player_units'] for r in steady)*0.03072/len(steady),copy_ms=sum(r['copy_units'] for r in steady)*0.03072/len(steady),capture_world_ms=sum(r['capture_world_units'] for r in steady)*0.03072/len(steady),capture_actor_ms=sum(r['capture_actor_units'] for r in steady)*0.03072/len(steady),capture_copy_ms=sum(r['capture_copy_units'] for r in steady)*0.03072/len(steady),capture_hash_ms=sum(r['capture_hash_units'] for r in steady)*0.03072/len(steady),actors_mean=sum(r['actors'] for r in steady)/len(steady))
    print('M15 telemetry',json.dumps(telemetry),flush=True)
    passed=34.3<=hz<=35.7 and not b['dropped'] and b['max_poll']*0.03072<100 and (not production or route or fps>4.6) and (not route or (nav_finish>=6 and door_open and max(r['item_count'] for r in rows)>rows[0]['item_count'] and occluded_retained))
    report=dict(telemetry=telemetry,logic_hz=hz,status='PASS' if passed else 'FAIL' ,frames=len(rows),md_simulation_ticks=0,controller_echo=True,exit_restored=True,rows=rows,
                scope='Independent 35 Hz CD logic; native MD renderer; delta world/R24 and word checksum on S2e only; profile counts are emulated VBlanks, not wall time or console FPS.',fast=fast,production=production)
    (rom.parent/('route_report.json' if route else 'live_deep_report.json' if fast and not production else 'live_report.json')).write_text(json.dumps(report,indent=2))
    assert 34.3<=hz<=35.7,('35 Hz cadence',hz)
    assert not b['dropped'],('dropped ticks',b['dropped'])
    assert b['max_poll']*0.03072<100,('stopwatch poll gap',b['max_poll'])
    if route:
        assert nav_finish>=6 and door_open and max(r['item_count'] for r in rows)>rows[0]['item_count'] and occluded_retained,('door/item/occluded actor route',nav_phase,nav_finish,door_open,occluded_retained)
    if production and not route:assert fps>4.6,('presentation target >4.6 FPS',fps)
    print('M15 LIVE PASS: actual movement/turn/fire, input echo, 2 Word RAM banks, exact world/actors, no MD logic, exit restored',flush=True)
finally:g.close()

