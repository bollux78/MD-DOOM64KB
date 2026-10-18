#!/usr/bin/env python3
"""R30: pure-stdlib native H40 art conversion from embedded Doom64KB 240x160 raw WAD.
320x224 real 4bpp pixels, BG_B tile images, 4x14 colours/tile-selectable palettes,
12-pixel top/bottom safe margins, per-tile RLE, original overlays on BG_A.
Run before the R30 build; generated .s/.h/.bin are intermediate build inputs.
"""
from pathlib import Path
import collections,hashlib,json,struct
ROOT=Path(__file__).resolve().parents[2]
WAD=ROOT/'scripts/doom64.wad'
NAMES=('TITLEPIC','WIMAP0','HELP2')
KEYS=('title','inter','final')
TEXT=((255,255,255),(255,40,40),(255,235,60),(200,200,200))

def lumps():
    b=WAD.read_bytes();assert b[:4]==b'IWAD'
    n=struct.unpack_from('>H',b,4)[0];ofs=struct.unpack_from('>I',b,8)[0]
    result={}
    for j in range(n):
        i=ofs+j*16;p,sz=struct.unpack_from('>IH',b,i)
        name=b[i+8:i+16].split(b'\0')[0].decode('latin1')
        assert p+sz<=len(b)
        result[name]=b[p:p+sz]
    return result

def wad_rgb(w):
    v=[((w>>8)&15)*4+(((w>>14)&1)*2)+(w>>15&1),
       ((w>>4)&15)*4+(((w>>13)&1)*2)+(w>>15&1),
       (w&15)*4+(((w>>12)&1)*2)+(w>>15&1)]
    return tuple(min(255,(x<<2)|(x>>4)) for x in v)

def mdword(rgb):
    r,g,b=(min(7,max(0,(int(v)+18)//36)) for v in rgb)
    return (b<<9)|(g<<5)|(r<<1)
def mdrgb(rgb):
    w=mdword(rgb)
    return tuple(((v<<5)|(v<<2)|(v>>1)) for v in ((w>>1)&7,(w>>5)&7,(w>>9)&7))
def error(a,b):
    return 3*(a[0]-b[0])**2+4*(a[1]-b[1])**2+2*(a[2]-b[2])**2

def median_cut(hist,rgbs):
    entries=[(i,count,rgbs[i]) for i,count in hist.items() if count]
    if not entries:return [(0,0,0)]*14
    boxes=[entries]
    while len(boxes)<14:
        candidates=[]
        for j,box in enumerate(boxes):
            extents=[max(t[2][ch] for t in box)-min(t[2][ch] for t in box) for ch in range(3)]
            score=max(extents)*sum(t[1] for t in box)**.35 if len(box)>1 else -1
            candidates.append((score,j,extents))
        _,idx,extents=max(candidates)
        if len(boxes[idx])<=1:break
        ch=max(range(3),key=lambda j:extents[j]*(3 if j==1 else 2))
        items=sorted(boxes.pop(idx),key=lambda t:t[2][ch])
        total=sum(t[1] for t in items)
        halfway=0;split=1
        for i,t in enumerate(items[:-1]):
            halfway+=t[1]
            if 2*halfway>=total:split=i+1;break
        boxes.extend((items[:split],items[split:]))
    result=[]
    for box in boxes:
        mass=sum(t[1] for t in box)
        avg=tuple(sum(t[1]*t[2][j] for t in box)//mass for j in range(3))
        rgb=mdrgb(avg)
        if rgb not in result:result.append(rgb)
    for _,_,rgb in sorted(entries,key=lambda t:-t[1]):
        value=mdrgb(rgb)
        if value not in result:result.append(value)
        if len(result)>=14:break
    return (result+[(0,0,0)]*14)[:14]

def tiles_for(raw):
    assert len(raw)==240*160
    result=[]
    for ty in range(28):
        for tx in range(40):
            tile=[]
            for yy in range(8):
                y=ty*8+yy
                for xx in range(8):
                    x=tx*8+xx
                    tile.append(-1 if y<12 or y>=212 else
                                raw[((y-12)*160//200)*240+x*240//320])
            result.append(tile)
    return result

def image_quantize(tiles,rgbs):
    groups=[]
    for tile in tiles:
        colors=[rgbs[i] for i in tile if i>=0]
        if not colors:groups.append(0);continue
        r,g,b=(sum(t[j] for t in colors)//len(colors) for j in range(3))
        groups.append(1 if r>=g+22 and r>=b+22 else
                      2 if g>=r+10 and g>=b+10 else
                      3 if b>=r+10 and b>=g+10 else 0)
    total=collections.Counter(i for tile in tiles for i in tile if i>=0)
    def palette():
        hist=[collections.Counter() for _ in range(4)]
        for tile,bank in zip(tiles,groups):
            hist[bank].update(i for i in tile if i>=0)
        return [median_cut(h if h else total,rgbs) for h in hist]
    pals=palette()
    for iteration in range(4):
        lookup=[[min(((error(rgbs[i],rgb),j+1) for j,rgb in enumerate(pals[bank])),
                     key=lambda p:p[0]) for i in range(256)] for bank in range(4)]
        changes=0
        for idx,tile in enumerate(tiles):
            hist=collections.Counter(i for i in tile if i>=0)
            bank=min(range(4),key=lambda g:sum(n*lookup[g][i][0] for i,n in hist.items()))
            if bank!=groups[idx]:groups[idx]=bank;changes+=1
        if not changes and iteration>0:break
        pals=palette()
    lookup=[[min(((error(rgbs[i],rgb),j+1) for j,rgb in enumerate(pals[bank])),
                 key=lambda p:p[0]) for i in range(256)] for bank in range(4)]
    for idx,tile in enumerate(tiles):
        hist=collections.Counter(i for i in tile if i>=0)
        groups[idx]=min(range(4),key=lambda g:sum(n*lookup[g][i][0] for i,n in hist.items()))
    return pals,groups,lookup

def pack_tile(tile):
    assert len(tile)==32
    out=bytearray();i=0
    while i<32:
        run=1
        while i+run<32 and tile[i+run]==tile[i] and run<128:run+=1
        if run>=3:
            out.extend((128+run-1,tile[i]));i+=run;continue
        st=i;i+=1
        while i<32:
            if i+2<32 and tile[i]==tile[i+1]==tile[i+2]:break
            i+=1
        out.append(i-st-1);out.extend(tile[st:i])
    return bytes((len(out),))+out if len(out)<32 else b'\0'+tile

def decode_one(buf,pos):
    tag=buf[pos];pos+=1
    if not tag:return buf[pos:pos+32],pos+32
    end=pos+tag;out=bytearray()
    while pos<end:
        t=buf[pos];pos+=1;n=(t&127)+1
        if t&128:out.extend([buf[pos]]*n);pos+=1
        else:out+=buf[pos:pos+n];pos+=n
    assert len(out)==32 and pos==end
    return bytes(out),pos

def main():
    d=lumps();pp=d['PLAYPAL'];rgbs=[wad_rgb(struct.unpack_from('>H',pp,i*2)[0]) for i in range(256)]
    results=[]
    for name,key in zip(NAMES,KEYS):
        src=d[name];tiles=tiles_for(src)
        pals,groups,lookup=image_quantize(tiles,rgbs)
        unique={};blobs=[];maps=[]
        for bank,tile in zip(groups,tiles):
            pix=[0 if color<0 else lookup[bank][color][1] for color in tile]
            raw=bytes(pix[q]*16+pix[q+1] for q in range(0,64,2))
            if raw not in unique:
                unique[raw]=len(unique);blobs.append(pack_tile(raw))
            maps.append((bank<<13)|unique[raw])
        packed=b''.join(blobs)
        pos=0
        for original in unique:
            decoded,pos=decode_one(packed,pos)
            assert decoded==original
        assert pos==len(packed)
        assert len(unique)<1250,(key,len(unique))
        pal=[]
        for bank in range(4):
            pal.extend(mdword(color) for color in [(0,0,0),*pals[bank],TEXT[bank]])
        assert len(pal)==64
        files={
            'pack':packed,
            'map':b''.join(struct.pack('>H',n) for n in maps),
            'pal':b''.join(struct.pack('>H',n) for n in pal)}
        for suffix,data in files.items():
            (ROOT/'res'/f'r30-{key}-{suffix}.bin').write_bytes(data)
        results.append(dict(name=name,key=key,tiles=len(unique),
                 packed_bytes=len(packed),map_bytes=len(files['map']),
                 palette_bytes=len(files['pal']),raw_source_bytes=len(src),
                 source_sha256=hashlib.sha256(src).hexdigest()))
    header=['/* Generated by scripts/lab/gen_r30_native.py. */',
            '#ifndef R30_STATIC_MANIFEST_H','#define R30_STATIC_MANIFEST_H']
    header.extend(f'#define R30_{item["key"].upper()}_TILES {item["tiles"]}u' for item in results)
    header+=['#endif','']
    (ROOT/'src/r30_static_manifest.h').write_text('\n'.join(header))
    asm=['/* R30 compressed native graphics, generated from original WAD. */',
         '.section .rodata','.balign 2']
    for key in KEYS:
        for suffix in ('pack','map','pal'):
            sym=f'r30_{key}_{suffix}'
            asm.extend(('.balign 2',f'.global {sym}',f'{sym}:',
                        f'  .incbin "res/r30-{key}-{suffix}.bin"'))
    (ROOT/'src/r30_static_data.s').write_text('\n'.join(asm)+'\n')
    report={'source_wad_sha256':hashlib.sha256(WAD.read_bytes()).hexdigest(),
            'mode':'H40/320x224, real 4bpp pixels, BG_B, 4x14-colour per-tile palette',
            'screens':results}
    print(json.dumps(report,indent=2))
    (ROOT/'res/r30-native-report.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
