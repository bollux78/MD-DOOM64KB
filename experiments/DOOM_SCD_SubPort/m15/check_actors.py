"""Audit compact values against actual native fields and the persistent graph."""
import struct

def expand(f):return (f&15)|((f&16)<<12)|((f&32)<<13)|((f&64)<<14)|((f&128)<<15)
def check_applied(g,frame,expected,sym,checked=True):
    want,actual,n,player,nr,linked,msize,snext,sprev,subsector,ssize,head=struct.unpack('>12I',g.readmem(0x61b040,48))
    assert (want,n,player,nr)==(expected['hash'],expected['n'],expected['player'],expected['nr']) and actual==(want if checked else 0)
    if checked:assert g.readmem(0x617000,n*24)==expected['actor_bytes'],('native compact values',frame)
    slots=struct.unpack('>%dH'%n,g.readmem(0x617c00,n*2));assert len(set(slots))==n and max(slots)<64
    ids=struct.unpack('>64H',g.readmem(0x618000,128));pool=g.readmem(0x614000,64*msize)
    offsets=struct.unpack('>8I',g.readmem(0x61b300,32));records={}
    for slot,v in zip(slots,expected['records']):
        off=slot*msize;assert ids[slot]==v[0];records[slot]=v
        typ=pool[off+offsets[0]]
        xyz=tuple(struct.unpack_from('>I',pool,off+k)[0] for k in offsets[1:4])
        angle,flags=(struct.unpack_from('>I',pool,off+k)[0] for k in offsets[4:6])
        sprite=pool[off+offsets[6]];fr=struct.unpack_from('>H',pool,off+offsets[7])[0]
        assert (typ,*xyz,angle,flags,sprite,fr)==(v[1],*(x&0xffffffff for x in v[2:5]),v[5]<<24,expand(v[6]),v[7],v[8]),('native field audit',frame,slot)
        ss=struct.unpack_from('>I',pool,off+subsector)[0]&0xffffff
        assert g.readmem(ss,1)[0]==v[9],'native subsector sector index'
    sectors=int.from_bytes(g.readmem(sym('_g_sectors'),4),'big')&0xffffff
    nsectors=int.from_bytes(g.readmem(sym('_g_numsectors'),2),'big')
    secraw=g.readmem(sectors,nsectors*ssize);seen=set()
    for s in range(nsectors):
        previous=sectors+s*ssize+head;ptr=struct.unpack_from('>I',secraw,s*ssize+head)[0]&0xffffff
        while ptr:
            offset=ptr-0x614000
            assert 0<=offset<64*msize and offset%msize==0
            slot=offset//msize;assert slot in records and slot not in seen
            seen.add(slot);v=records[slot];assert v[9]==s and not(v[6]&8)
            assert struct.unpack_from('>I',pool,offset+sprev)[0]&0xffffff==previous
            previous=ptr+snext;ptr=struct.unpack_from('>I',pool,offset+snext)[0]&0xffffff
    assert len(seen)==linked==sum(not(v[6]&8) for v in expected['records'])
