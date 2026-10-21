#!/usr/bin/env python3
"""R47B-SIM: host VDP composition, layout and DMA budget oracles.
NOT actual Nuked/MiSTer RTL timing or a Mega Drive ROM.
"""
import argparse, json, random
from pathlib import Path
W,H=76,44
SCREEN_W,SCREEN_H=304,224
MAP_H=32
ROWS,COLS=21,38

def region(a,n): return set(range(a,a+n))

def examine_layout(a,b,window,hscroll,sat,pair_index=256):
    bases=(a,b,window,hscroll,sat)
    font=min(bases)-96*32
    assert 0<=font and font%32==0
    pair=region(pair_index*32,256*32)
    eight=region(16*32,226*32)
    glyph=region(font,96*32)
    tables=(("A",region(a,4096)),("B",region(b,4096)),
            ("Window",region(window,4096)),
            ("HScroll",region(hscroll,1024)),("SAT",region(sat,1024)))
    assert pair.isdisjoint(eight) and pair.isdisjoint(glyph)
    assert eight.isdisjoint(glyph)
    for name,reg in tables:
        assert pair.isdisjoint(reg) and eight.isdisjoint(reg) and glyph.isdisjoint(reg),name
    return {"font_vram":f"{font:04X}","font_index":font//32,
            "window_sat_overlap":not tables[2][1].isdisjoint(tables[4][1]),
            "window_hscroll_overlap":not tables[2][1].isdisjoint(tables[3][1])}

def layout_oracle():
    dual=examine_layout(0xE000,0xC000,0xD000,0xF000,0xF400)
    assert dual["font_vram"]=="B400" and dual["font_index"]==1440
    assert not dual["window_sat_overlap"]
    # Standalone R22 starts with min E000 => font D400, then a prototype
    # B=D000 shifts it to min D000 => font C400. It triggers relocation,
    # NOT direct font/Plane B overlap.
    assert min(0xE000,0xE000,0xF000,0xFC00,0xFC00)-3072==0xD400
    trial=examine_layout(0xE000,0xD000,0xF000,0xFC00,0xFC00)
    assert trial["font_vram"]=="C400" and trial["window_sat_overlap"]
    assert 0xF000+22*128==0xFB00 and 0xF000+24*128==0xFC00
    return {"dual_no_sgdk_font_relocation":dual,
            "standalone_proto_font_relocated":trial,
            "standalone_previous_font":"D400",
            "rule":"Never access standalone F000 Window rows 24..31 (SAT/HScroll alias)"}

def framebuffer(rng):
    return [[rng.randrange(16) if rng.randrange(7) else 0 for x in range(W)]
            for y in range(H)]

def glyph(r,c,ty,tx):
    return 15 if (r*11+c*13+ty*5+tx*7)%6==0 else 0

def ref_pixel(fb,y,x,window=False):
    r,ty=divmod(y,8);c,tx=divmod(x,8)
    val=fb[2*r+(ty>=4)][2*c+(tx>=4)] if 1<=r<=ROWS else glyph(r,c,ty,tx)
    return (glyph(r,c,ty,tx) or val) if window else val

def pair_pixel(fb,y,x,window=False,black_menu=False):
    r,ty=divmod(y,8);c,tx=divmod(x,8)
    a=(fb[2*r][2*c+(tx>=4)] if ty<4 else 0) if 1<=r<=ROWS else glyph(r,c,ty,tx)
    source=(y-4)%(MAP_H*8)
    br,by=divmod(source,8)
    b=fb[2*br+1][2*c+(tx>=4)] if 1<=br<=ROWS and by<4 else 0
    if window: a=glyph(r,c,ty,tx)
    if window and black_menu: b=0
    return a or b

def pixel_oracle(frames):
    rng=random.Random(0x47B)
    for trial in range(frames):
        fb=framebuffer(rng)
        for y in range(SCREEN_H):
            for x in range(SCREEN_W):
                a=ref_pixel(fb,y,x);b=pair_pixel(fb,y,x)
                if a!=b:raise AssertionError((trial,y,x,a,b))
    fb=framebuffer(rng)
    differences=sum(ref_pixel(fb,y,x,True)!=pair_pixel(fb,y,x,True)
                    for y in range(64,120) for x in range(80,224))
    assert differences>0,"WINDOW underlay limitation must be explicit"
    return {"frames":frames,"matching_pixels":frames*SCREEN_W*SCREEN_H,
            "window_overlay_mismatches":differences,
            "window_underlay_is_not_identical":True}

def dma_oracle():
    assert 256*32==8192 and 38*21*32==25536
    assert 42*76==3192 and 3192<7200
    assert 22*76==1672 and 1672<=2128
    return {"patterns_once_bytes":8192,"legacy_max_pattern_upload_bytes_per_frame":25536,
            "plane_pair_pattern_upload_per_frame":0,"plane_pair_map_dma_bytes":3192,
            "dma_commands":42,"ntsc_nominal_dma_bytes_per_vblank":7200,
            "includes_vdp_fifo_register_overhead":False,
            "hardware_vblank_deadline_proven":False,
            "old_standalone_fb_plus_map_bytes":3268,
            "new_standalone_fb_bytes":3344,
            "dual_uses_two_halves_each_bytes":1672}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="")
    p.add_argument("--frames",type=int,default=48)
    a=p.parse_args()
    assert 1<=a.frames<=1000
    result={"kind":"host software oracle, NOT MiSTer RTL timing",
            "layout":layout_oracle(),"pixels":pixel_oracle(a.frames),
            "dma":dma_oracle(),
            "result":"PASS: plane-pair semantics/layout verified; FPGA timing still unmeasured"}
    if a.out:
        dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
