"""Independent pointer-free decoder and applied native MD sprite graph check."""
import struct

def mix(h,x):return ((h^(x&0xffffffff))*16777619)&0xffffffff

def decode_actors(g):
    magic,version,count,nrom,used,want,stride,res=struct.unpack('>8I',g.readmem(0x608000,32))
    assert (magic,version,count,stride,res)==(0x53324342,1,27,36,0)
    assert nrom<=512 and 256<=used<=49152 and used%4==0
    raw=g.readmem(0x608000,used);h=2166136261
    for i,x in enumerate(raw):h=mix(h,0 if 20<=i<24 else x)
    assert h==want,'actor stream checksum'
    offsets=struct.unpack_from('>27I',raw,32);rom={};frames=[];previous={};known={}
    changes=dict(spawn=0,remove=0,position=0,animation=0,rom_removed=0,rom_restored=0)
    for frame,off in enumerate(offsets):
        assert off>=256 and off%4==0 and off+16<=used
        tic,n,nr,want,player,res=struct.unpack_from('>IHHIHH',raw,off)
        assert tic==frame*100 and 0<n<=64 and nr<=nrom and not res
        p=off+16;actors={};records=[]
        for j in range(n):
            v=struct.unpack_from('>HHiiiIIHHHhhH',raw,p);p+=36
            id,type,*_=v
            assert id and id not in actors
            assert id not in known or known[id]==type,'stable ID reused for another type'
            known[id]=type;actors[id]=v;records.append(v)
            if id in previous:
                changes['position']+=v[2:5]!=previous[id][2:5]
                changes['animation']+=v[7:10]!=previous[id][7:10]
        assert player in actors
        if frame:
            changes['spawn']+=len(actors.keys()-previous.keys())
            changes['remove']+=len(previous.keys()-actors.keys())
        actor_bytes=raw[off+16:p];seen=set()
        for j in range(nr):
            id,dead,delay,res=struct.unpack_from('>4H',raw,p);p+=8
            assert id<nrom and dead in (0,1) and not res and id not in seen
            seen.add(id)
            if frame:
                changes['rom_removed']+=dead>rom[id][0]
                changes['rom_restored']+=dead<rom[id][0]
            rom[id]=(dead,delay)
        assert len(rom)==nrom
        assert p==(offsets[frame+1] if frame<26 else used)
        h=2166136261
        for x in [n,nrom,player]+[x for v in records for x in v]+[x for i in range(nrom) for x in rom[i]]:h=mix(h,x)
        assert h==want,('canonical actors',frame,hex(h),hex(want))
        frames.append(dict(hash=want,n=n,nr=nr,player=player,records=records,actor_bytes=actor_bytes))
        previous=actors
    assert changes['position'] and changes['animation'],'dynamic actors not exercised'
    assert changes['spawn'] and changes['remove'],'actor lifetime not exercised'
    stats=dict(bytes=used,romthings=nrom,max_live=max(f['n'] for f in frames),stable_ids=len(known),changes=changes)
    print('S2c decoded real actors',stats,flush=True)
    return frames,stats

def check_applied(g,frame,expected,sym,checked=True):
    want,actual,n,player,nr,linked,msize,snext,sprev,subsector,ssize,head=struct.unpack('>12I',g.readmem(0x61b040,48))
    assert (want,n,player,nr)==(expected['hash'],expected['n'],expected['player'],expected['nr']) and actual==(want if checked else 0)
    assert g.readmem(0x617000,n*36)==expected['actor_bytes'],('native applied actor values',frame)
    assert msize*64<=0x3000 and snext+4<=msize and sprev+4<=msize and head+4<=ssize
    sectors=int.from_bytes(g.readmem(sym('_g_sectors'),4),'big')&0xffffff
    nsectors=int.from_bytes(g.readmem(sym('_g_numsectors'),2),'big')
    assert 0<nsectors<=256
    secraw=g.readmem(sectors,nsectors*ssize);pool=g.readmem(0x614000,n*msize);seen=set()
    for s in range(nsectors):
        previous=sectors+s*ssize+head
        ptr=struct.unpack_from('>I',secraw,s*ssize+head)[0]&0xffffff
        while ptr:
            offset=ptr-0x614000
            assert 0<=offset<n*msize and offset%msize==0
            i=offset//msize;assert i not in seen
            seen.add(i);v=expected['records'][i]
            assert v[12]==s and not (v[6]&8),'wrong native sector membership'
            assert struct.unpack_from('>I',pool,offset+sprev)[0]&0xffffff==previous
            previous=ptr+snext;ptr=struct.unpack_from('>I',pool,offset+snext)[0]&0xffffff
    assert len(seen)==linked==sum(not(v[6]&8) for v in expected['records'])
