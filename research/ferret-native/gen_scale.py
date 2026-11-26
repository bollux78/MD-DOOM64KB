"""Generate 68000 column scalers (one unrolled routine per scaler row) from sc_scalers in scene.h.

Row y of scaler s:  even y:  move.b SC(a1),2y(a0)            odd y:  move.b SC(a1),d0
                                                                     move.b 0(a2,d0.w),2y(a0)   (nibble swap LUT)
                    then     dbra d6,<row y+1> ; rts
Entry: a0 = column base (pixel(x,0)), a1 = texture block base (texel = a1+SC), a2 = 256-byte swap table,
d0 = 0 (upper bits), d6 = rows-1; jump to fr_gs_rows[s*72+y0]. Same bytes as the table kernel for the no-wrap case.
"""
import re,sys,pathlib
def main():
    scene=pathlib.Path(sys.argv[1]).read_text();out=pathlib.Path(sys.argv[2])
    m=re.search(r"static const int16_t sc_scalers\[(\d+)\] = \{([^}]*)\};",scene)
    if not m or "#define SC_ART_PAIR 1" not in scene:
        out.write_text("    .text\n    .globl fr_gs_rows\n    .even\nfr_gs_rows:\n    .long 0\n");return 0
    vals=[int(v) for v in m.group(2).replace("\n"," ").split(",") if v.strip()]
    H=72;assert len(vals)%H==0;S=len(vals)//H
    L=["    .text","    .even"]
    for s in range(S):
        for y in range(H):
            sc=vals[s*H+y];assert -32768<=sc<=32767
            L.append(f"gs{s}_{y}:")
            if y%2==0:L.append(f"    move.b {sc}(%a1),{2*y}(%a0)")
            else:L+= [f"    move.b {sc}(%a1),%d0",f"    move.b 0(%a2,%d0.w),{2*y}(%a0)"]
            if y<H-1:L.append(f"    dbra %d6,gs{s}_{y+1}")
            L.append("    rts")
    L+=["    .globl fr_gs_rows","    .even","fr_gs_rows:"]
    for s in range(S):
        for y in range(0,H,8):L.append("    .long "+",".join(f"gs{s}_{yy}" for yy in range(y,min(H,y+8))))
    out.write_text("\n".join(L)+"\n");return S
if __name__=="__main__":print("GEN SCALERS",main())
