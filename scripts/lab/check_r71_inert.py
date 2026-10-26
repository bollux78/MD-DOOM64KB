#!/usr/bin/env python3
"""Ensure R71 guarded source is EXACTLY inert when R70-A and R71 flags are undefined.
Uses the proven R70-A resolver for its existing A2 block after removing ONLY the two R71 additions.
Build workflow separately asserts rebuilt R66 SHA256 and binary equality.
"""
import difflib,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_r70_inert import resolve,norm

a,b=map(Path,sys.argv[1:3])
draw=(b/'src/r_draw.c').read_text()
before="""#elif defined(DOOM_R71_B1B)
extern void R71_DrawColumnWallFast(const draw_column_vars_t *);
#define R20_WALL_DRAW(v) R71_DrawColumnWallFast(v)
#else
#define R20_WALL_DRAW(v) R_DrawColumnWall(v)"""
after="""#else
#define R20_WALL_DRAW(v) R_DrawColumnWall(v)"""
assert draw.count(before)==1
draw=draw.replace(before,after)
draw=resolve(draw)
video=(b/'src/r22_video.inc').read_text()
start=video.index('/* R71-OFS: two pure ROM tables')
end=video.index('/* R42 Q2:',start)
video=video[:start]+video[end:]
video=video.replace('R71_PixelByte(r22_fb.pixels','R22_PixelByte(r22_fb.pixels')
start=video.index('/* R71-B1b: wall-only fast entry')
end=video.index('void R_DrawFuzzColumn(',start)
video=video[:start]+video[end:]
ok=True
for name,new in (('src/r_draw.c',draw),('src/r22_video.inc',video)):
    original=norm((a/name).read_text())
    got=norm(new)
    same=original==got
    ok=ok and same
    print(('PASS' if same else 'FAIL')+' inert '+name)
    if not same:
        print('\n'.join(list(difflib.unified_diff(original,got,lineterm=''))[:55]))
sys.exit(0 if ok else 1)
