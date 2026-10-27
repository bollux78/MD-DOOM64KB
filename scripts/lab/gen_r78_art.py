#!/usr/bin/env python3
"""Lossless RGB -> two-plane Mega Drive art from user-supplied MD PNGs.

Base BG_B is opaque and approximates rare missing colors; BG_A corrects those
pixels exactly. Without glyph overlays the decoded RGB image equals the PNG.
Palette sets are pinned offline results, not another dithering pass.
"""
from pathlib import Path
import argparse,hashlib,itertools,json,re,struct
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'assets/art'
LEVELS=np.array([0,36,73,109,146,182,219,255],dtype=np.uint8)

def encode(path,spec):
    source=path.read_bytes();assert hashlib.sha256(source).hexdigest()==spec['sha256']
    im=Image.open(path).convert('RGB');assert im.size==(320,224)
    pixels=np.asarray(im);colors,index=np.unique(pixels.reshape(-1,3),axis=0,return_inverse=True)
    assert np.isin(colors,LEVELS).all(),'input has non-MD channel values'
    tiles=index.reshape(28,8,40,8).transpose(0,2,1,3).reshape(1120,64)
    hist=np.array([np.bincount(t,minlength=len(colors)) for t in tiles]);present=hist>0
    palettes=[np.asarray(p,int) for p in spec['palettes']]
    assert [len(p) for p in palettes]==[14,15,15,15]
    assert all(len(set(p))==len(p) and min(p)>=0 and max(p)<len(colors) for p in palettes)
    masks=np.zeros((4,len(colors)),bool)
    lut=np.zeros((4,len(colors)),np.uint8)
    nearest=np.zeros_like(lut)
    for bank,pal in enumerate(palettes):
        masks[bank,pal]=1;lut[bank,pal]=np.arange(1,len(pal)+1)
        errors=(((colors[:,None].astype(float)-colors[pal][None,:])**2)*[3,4,2]).sum(2)
        nearest[bank]=errors.argmin(1)+1
    pairs=list(itertools.product(range(4),repeat=2))
    patterns={};mapsA=[];mapsB=[];corrections=0;corrected_tiles=0
    def intern(p):
        raw=bytes((p[::2]<<4)|p[1::2]);return patterns.setdefault(raw,len(patterns))
    for t,tile in enumerate(tiles):
        def cost(pair):
            a,b=pair
            return (int(np.sum(present[t]&~(masks[a]|masks[b]))),int(hist[t,~masks[a]].sum()),a,b)
        a,b=min(pairs,key=cost)
        assert cost((a,b))[0]==0,('uncovered colors',t)
        missing=~masks[a,tile]
        base=nearest[a,tile].copy();overlay=np.where(missing,lut[b,tile],0).astype(np.uint8)
        base[~missing]=lut[a,tile[~missing]]
        assert min(base)>0 and max(base)<=15
        assert np.all(overlay[missing]>0)
        mapsB.append((a<<13)|intern(base));mapsA.append((b<<13)|intern(overlay))
        corrections+=int(missing.sum());corrected_tiles+=bool(missing.any())
    raw=b''.join(patterns)
    assert len(patterns)==spec['expected_tiles'],(len(patterns),spec['expected_tiles'])
    assert 16+len(patterns)<1440,'picture overlaps SGDK font'
    palette=[]
    for bank,pal in enumerate(palettes):
        rgb=[(0,0,0),*map(tuple,colors[pal])]
        if bank==0:rgb.append((255,255,255)) # existing native text uses PAL0/15
        assert len(rgb)==16
        for r,g,b in rgb:palette.append(((int(b)>>5)<<9)|((int(g)>>5)<<5)|((int(r)>>5)<<1))
    assert len(palette)==64
    # Decode the emitted tile bytes/map words/CRAM, not just source indices.
    decoded=np.zeros_like(pixels)
    for t,(ma,mb) in enumerate(zip(mapsA,mapsB)):
        for q in range(64):
            def nib(m):
                v=raw[(m&0x7ff)*32+q//2]
                return (v>>4) if q%2==0 else v&15
            a,b=nib(ma),nib(mb)
            value=palette[((ma>>13)&3)*16+a] if a else palette[((mb>>13)&3)*16+b]
            c=[int(LEVELS[(value>>shift)&7]) for shift in (1,5,9)]
            y=(t//40)*8+q//8;x=(t%40)*8+q%8;decoded[y,x]=c
    assert np.array_equal(decoded,pixels),'decoded VDP picture differs from input PNG'
    return dict(pack=raw,map=struct.pack('>1120H',*mapsA),mapb=struct.pack('>1120H',*mapsB),pal=struct.pack('>64H',*palette)),decoded,dict(
        source_sha256=spec['sha256'],source_filename=spec['original_filename'],width=320,height=224,
        source_colors=len(colors),tiles=len(patterns),foreground_correction_pixels=corrections,
        foreground_correction_tiles=corrected_tiles,decoded_changed_pixels=0,
        decoded_rgb_sha256=hashlib.sha256(decoded.tobytes()).hexdigest(),
        mode='BG_B opaque base + BG_A sparse exact correction; no redither, no resize',
        overlay_note='Menu/stat glyphs replace correction cells while visible; their transparent background reveals the approximate base. Retiring glyphs restores the exact correction map.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--verify-only',action='store_true');args=ap.parse_args()
    config=json.loads((ASSETS/'r78-palettes.json').read_text());reports={}
    for key,spec in config.items():
        blobs,decoded,report=encode(ASSETS/spec['file'],spec);reports[key]=report
        if not args.verify_only:
            (ROOT/'res').mkdir(exist_ok=True)
            for suffix,data in blobs.items():(ROOT/'res'/f'r30-{key}-{suffix}.bin').write_bytes(data)
            Image.fromarray(decoded).save(ROOT/'res'/f'r78-{key}-decoded.png')
        print('PASS R78 lossless',key,json.dumps(report),flush=True)
    if args.verify_only:return
    header=ROOT/'src/r30_static_manifest.h';text=header.read_text()
    for key,report in reports.items():
        text,n=re.subn(r'(#define R30_'+key.upper()+r'_TILES )\d+u',r'\g<1>'+str(report['tiles'])+'u',text)
        assert n==1
    header.write_text(text)
    asm=ROOT/'src/r30_static_data.s';text=asm.read_text()
    for key in reports:
        symbol=f'r30_{key}_mapb';assert symbol not in text
        text+=f'\n.balign 4\n.global {symbol}\n{symbol}:\n  .incbin "res/r30-{key}-mapb.bin"\n'
    asm.write_text(text)
    (ROOT/'res/r78-art-report.json').write_text(json.dumps(reports,indent=2)+'\n')

if __name__=='__main__':main()
