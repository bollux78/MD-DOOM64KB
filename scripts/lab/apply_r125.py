#!/usr/bin/env python3
"""R125: conservative 2D ray/half-plane fast reject for BSP bounding boxes.
Apply after R119 both + R122 layout. No ray-based wall sampling: BSP remains the authority.
Test only: control R122 layout versus candidate; do not promote until pixel/logic parity.
"""
from pathlib import Path
p=Path('src/r_draw.c');s=p.read_text()
def rep(a,b):
    global s
    assert s.count(a)==1,(a[:100],s.count(a))
    s=s.replace(a,b)
rep('static boolean R_CheckBBox(const int16_t __far* bspcoord)\n{',
'''/* R125: two outward-facing rays conservatively reject a BSP bbox
   wholly outside the FOV before the expensive R_PointToAngle16 calls.
   Direction components quantized to 1/512 of fixed-point unit; ray
   boundaries expanded by 5.625 degrees and 1024 cross units for slack.
   The original R_CheckBBox still decides every non-rejected bbox. */
static int16_t r125_lx,r125_ly,r125_rx,r125_ry;
static void R125_UpdateRays(void)
{
    angle16_t a=(angle16_t)(viewangle16+clipangle+0x0400u);
    angle16_t b=(angle16_t)(viewangle16-clipangle-0x0400u);
    r125_lx=(int16_t)(finecosineapprox(a>>ANGLETOFINESHIFT_16)>>9);
    r125_ly=(int16_t)(finesineapprox(a>>ANGLETOFINESHIFT_16)>>9);
    r125_rx=(int16_t)(finecosineapprox(b>>ANGLETOFINESHIFT_16)>>9);
    r125_ry=(int16_t)(finesineapprox(b>>ANGLETOFINESHIFT_16)>>9);
}
static boolean R125_BBoxOutsideRays(const int16_t __far* b)
{
    const int32_t vx=viewx>>FRACBITS,vy=viewy>>FRACBITS;
    /* cross(d,p-v)=dx*(py-vy)-dy*(px-vx).
       For a complete AABB, select extrema analytically (only 2 corners).
       Quantization and a positive margin favor keeping boxes, not rejection. */
    const int32_t ylo=(r125_lx>=0?b[BOXBOTTOM]:b[BOXTOP])-vy;
    const int32_t xlo=(r125_ly>0?b[BOXRIGHT]:b[BOXLEFT])-vx;
    const int32_t minleft=(int32_t)r125_lx*ylo-(int32_t)r125_ly*xlo;
    if(minleft>1024) return true;
    const int32_t yhi=(r125_rx>=0?b[BOXTOP]:b[BOXBOTTOM])-vy;
    const int32_t xhi=(r125_ry>0?b[BOXLEFT]:b[BOXRIGHT])-vx;
    const int32_t maxright=(int32_t)r125_rx*yhi-(int32_t)r125_ry*xhi;
    return maxright < -1024;
}
static boolean R_CheckBBox(const int16_t __far* bspcoord)
{''')
rep('''    R37_HIT(R37_BBOX);
    // Find the corners of the box''','''    R37_HIT(R37_BBOX);
    if(R125_BBoxOutsideRays(bspcoord)) return false;
    // Find the corners of the box''')
rep('''    R_RenderBSPNode (numnodes-1);''','''    R125_UpdateRays();
    R_RenderBSPNode (numnodes-1);''')
p.write_text(s)
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text()
assert s.count("'r122-'")==1 and s.count("('layout', 1)")==1
p.write_text(s.replace("'r122-'","'r125-'").replace("('layout', 1)","('raybbox', 1)"))
print('R125 raybbox: outward 2D FOV rays as conservative early BSP bbox rejection')
