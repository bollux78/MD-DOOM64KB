#!/usr/bin/env python3
"""R47A standalone plane-pair vs R22 dynamic-tile compositor pixel oracle.
Independent of VDP/SDK timing. Deliberately does NOT claim hardware safety.
"""
import random
W,H=76,44
PIXELS=304
SCREEN=224
COLS=38
PAIRS=22
TILE_HEIGHT=8
rng=random.Random(0x47A)
def frame():
    return [[rng.randrange(16) for _ in range(W)] for _ in range(H)]
def pix_current(fb,x,y):
    tr,ty=divmod(y,8);tc,tx=divmod(x,8)
    if not 1<=tr<=21:return None
    row=2*tr+(ty>=4)
    col=2*tc+(tx>=4)
    return fb[row][col]
def pix_pair(fb,x,y):
    tr,ty=divmod(y,8);tc,tx=divmod(x,8)
    if not 1<=tr<=21:return None
    # Plane A stores line 2*tr at top half; B stores line 2*tr+1
    # at top half but its vscroll -4 moves it into bottom half.
    row=2*tr+(ty>=4)
    col=2*tc+(tx>=4)
    return fb[row][col]
# Generic VDP mapping logic verifying scroll/shading independently:
def draw_pair(fb, plane, sy, sx):
    tc,tx=divmod(sx,8)
    source_y=sy if plane=='A' else (sy-4)%(32*8)
    tr,ty=divmod(source_y,8)
    if ty>=4 or not 1<=tr<=21:return 0
    src_row=2*tr+(plane=='B')
    return fb[src_row][2*tc+(tx>=4)]
def current_3d(fb,sy,sx):
    tr,ty=divmod(sy,8)
    if not 1<=tr<=21:return 0
    return fb[2*tr+(ty>=4)][2*(sx//8)+(sx%8>=4)]
def check():
    for t in range(40):
        fb=frame()
        for sy in range(SCREEN):
            for sx in range(PIXELS):
                cur=current_3d(fb,sy,sx)
                # A nonzero color wins; 0 is transparent and shows B/backdrop.
                a=draw_pair(fb,'A',sy,sx)
                b=draw_pair(fb,'B',sy,sx)
                composed=a or b
                if composed!=cur:
                    raise AssertionError((t,sy,sx,cur,a,b))
    print('R47A PASS: 40 random 76x44 frames, exact 4x4 pixel equivalence outside WINDOW menus')
    # A known and explicit caveat for an overlay WINDOW with transparent pixels.
    # Visible B odd sample cannot reproduce the complete current-plane raster.
    fb=frame()
    differences=0
    for sy in range(64,104):
        for sx in range(80,224):
            if (sx+sy)%3==0: continue  # opaque menu glyph; differences hidden
            old=current_3d(fb,sy,sx)
            under=draw_pair(fb,'B',sy,sx)
            differences+=(old!=under)
    assert differences>0
    print('R47A KNOWN LIMITATION: menu WINDOW over 3D changes background pixels; must handle explicitly')
if __name__=='__main__':check()
