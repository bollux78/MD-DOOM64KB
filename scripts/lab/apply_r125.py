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
typedef struct { int16_t lx,ly,rx,ry; } R125_Rays;
static void R125_UpdateRays(R125_Rays* rays)
{
    angle16_t a=(angle16_t)(viewangle16+clipangle+0x0400u);
    angle16_t b=(angle16_t)(viewangle16-clipangle-0x0400u);
    rays->lx=(int16_t)(finecosineapprox(a>>ANGLETOFINESHIFT_16)>>9);
    rays->ly=(int16_t)(finesineapprox(a>>ANGLETOFINESHIFT_16)>>9);
    rays->rx=(int16_t)(finecosineapprox(b>>ANGLETOFINESHIFT_16)>>9);
    rays->ry=(int16_t)(finesineapprox(b>>ANGLETOFINESHIFT_16)>>9);
}
static boolean R125_BBoxOutsideRays(const int16_t __far* b, const R125_Rays* rays)
{
    const int32_t vx=viewx>>FRACBITS,vy=viewy>>FRACBITS;
    /* cross(d,p-v)=dx*(py-vy)-dy*(px-vx).
       For a complete AABB, select extrema analytically (only 2 corners).
       Quantization and a positive margin favor keeping boxes, not rejection. */
    const int32_t ylo=(rays->lx>=0?b[BOXBOTTOM]:b[BOXTOP])-vy;
    const int32_t xlo=(rays->ly>0?b[BOXRIGHT]:b[BOXLEFT])-vx;
    const int32_t minleft=(int32_t)rays->lx*ylo-(int32_t)rays->ly*xlo;
    if(minleft>1024) return true;
    const int32_t yhi=(rays->rx>=0?b[BOXTOP]:b[BOXBOTTOM])-vy;
    const int32_t xhi=(rays->ry>0?b[BOXLEFT]:b[BOXRIGHT])-vx;
    const int32_t maxright=(int32_t)rays->rx*yhi-(int32_t)rays->ry*xhi;
    return maxright < -1024;
}
static boolean R_CheckBBox(const int16_t __far* bspcoord, const R125_Rays* rays)
{''')
rep('''    R37_HIT(R37_BBOX);
    // Find the corners of the box''','''    R37_HIT(R37_BBOX);
    if(R125_BBoxOutsideRays(bspcoord,rays)) return false;
    // Find the corners of the box''')
# Pass the stack-local ray state down the iterative BSP walk. Neither BSS nor DATA grows.
rep('''#define MAX_BSP_DEPTH 64

static void R_RenderBSPNode(int16_t bspnum)
{
    R20_PROBE();''', '''#define MAX_BSP_DEPTH 64

static void R_RenderBSPNode(int16_t bspnum)
{
    R125_Rays rays;
    R125_UpdateRays(&rays);
    R20_PROBE();''')
# The recursive fallback is not built in our production configuration, but must compile too.
rep('''#else
static void R_RenderBSPNode(int16_t bspnum)
{
    R20_PROBE();''','''#else
static void R_RenderBSPNodeInner(int16_t bspnum, const R125_Rays* rays)
{
    R20_PROBE();''')
rep('''\tR_RenderBSPNode(bsp->children[side]); // recursively divide front space''','''    R_RenderBSPNodeInner(bsp->children[side],rays); // recursively divide front space''')
rep('''\t\tR_RenderBSPNode(bsp->children[side ^ 1]);''','''        R_RenderBSPNodeInner(bsp->children[side ^ 1],rays);''')
rep('''}
#endif


static void R_ClearDrawSegs(void)''','''}
static void R_RenderBSPNode(int16_t bspnum)
{
    R125_Rays rays;
    R125_UpdateRays(&rays);
    R_RenderBSPNodeInner(bspnum,&rays);
}
#endif


static void R_ClearDrawSegs(void)''')
assert s.count('R7_VALUE(10, R_CheckBBox(bsp->bbox[side]))')==1
assert s.count('R7_VALUE(10, R_CheckBBox(bsp->bbox[side ^ 1]))')==1
s=s.replace('R7_VALUE(10, R_CheckBBox(bsp->bbox[side]))','R7_VALUE(10, R_CheckBBox(bsp->bbox[side],&rays))')
s=s.replace('R7_VALUE(10, R_CheckBBox(bsp->bbox[side ^ 1]))','R7_VALUE(10, R_CheckBBox(bsp->bbox[side ^ 1],rays))')
p.write_text(s)
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text()
assert s.count("'r122-'")==1 and s.count("('layout', 1)")==1
p.write_text(s.replace("'r122-'","'r125-'").replace("('layout', 1)","('raybbox', 1)"))
print('R125 raybbox: outward 2D FOV rays as conservative early BSP bbox rejection')
