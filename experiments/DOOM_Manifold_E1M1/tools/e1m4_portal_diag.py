#!/usr/bin/env python3
"""E1M4 portal-cut diagnostic, applied ONLY to a disposable staged Manifold tree.

Modes:
  trace      Record early returns per screen-column window and overlay open yclip
             spans AFTER traversal (not a visual fix).
  depth48    32 -> 48 traversal-depth limit, revisits unchanged.
  revisit12  5 -> 12 sector visits per frame, depth unchanged.
  both       depth48 + revisit12.
  control    No changes.

No changes to the upstream Manifold checkout, DOOM R128 or M14 branches.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def replace_exact(path: Path, old: str, new: str, n: int = 1) -> None:
    src = path.read_text()
    actual = src.count(old)
    if actual != n:
        raise RuntimeError(f"{path}: expected {n} occurrences, found {actual}: {old[:120]!r}")
    path.write_text(src.replace(old, new, n))


def apply_trace(src: Path) -> None:
    portal = src / "portal.c"
    draw = src / "draw.c"

    anchor = "void visit_graph(u16 src_sector, u16 sector, u16 x1, u16 x2, u32 cur_frame, uint8_t depth) {"
    support = """
/* E1M4 controlled experiment: rejected windows, NOT a visibility oracle.
   Bit 1=depth, 2=active cycle, 4=visit budget, 8=origin guard, 16=stack guard.
   Count *calls rejected*, not number of missing walls. */
static u8 e1m4_diag_window_mask[RENDER_WIDTH];
static volatile u16 e1m4_diag_rejects[5];
void e1m4_diag_draw(const u8* masks, const volatile u16* counts);
static void e1m4_diag_reject(u16 x1, u16 x2, u8 bit, u8 index) {
    if (e1m4_diag_rejects[index] != 65535u) e1m4_diag_rejects[index]++;
    if (x1 > RENDER_WIDTH) x1 = RENDER_WIDTH;
    if (x2 > RENDER_WIDTH) x2 = RENDER_WIDTH;
    for (u16 x=x1; x<x2; x++) e1m4_diag_window_mask[x] |= bit;
}
"""
    replace_exact(portal, anchor, support + anchor)
    replace_exact(portal,
        "if(depth >= MAX_DEPTH ) {",
        "if(depth >= MAX_DEPTH ) { e1m4_diag_reject(x1,x2,1,0);")
    replace_exact(portal,
        "if(sector_rendered_cache[sector] & 0b1) {",
        "if(sector_rendered_cache[sector] & 0b1) { e1m4_diag_reject(x1,x2,2,1);")
    replace_exact(portal,
        "if(sector_rendered_cache[sector] >= 10) {",
        "if(sector_rendered_cache[sector] >= 10) { e1m4_diag_reject(x1,x2,4,2);")
    # A separate safety gate can abort before MAX_DEPTH; trace it too.
    replace_exact(portal,
        "if (depth > 48 || (sp_now & 0xFFFFFF) < ((manifold_heap_high & 0xFFFFFF) + 3072)) { manifold_dbg[7]++; return; }",
        "if (depth > 48 || (sp_now & 0xFFFFFF) < ((manifold_heap_high & 0xFFFFFF) + 3072)) { e1m4_diag_reject(x1,x2,16,4); manifold_dbg[7]++; return; }")
    replace_exact(portal,
        "if(sector == src_sector && depth != 0) { return; }",
        "if(sector == src_sector && depth != 0) { e1m4_diag_reject(x1,x2,8,3); return; }")

    start = "void portal_rend(u16 src_sector, u32 cur_frame) {"
    replace_exact(portal, start, start + """
    for (u16 x=0; x<RENDER_WIDTH; x++) e1m4_diag_window_mask[x] = 0;
    for (u16 i=0; i<5; i++) e1m4_diag_rejects[i] = 0;
""")
    # This occurs at the unique end of portal_rend, after normal recursion.
    marker = """    KLog("Rendered.");
    #endif
    return;
    #ifdef DEBUG_PORTAL_CLIP"""
    replace_exact(portal, marker, """    KLog("Rendered.");
    #endif
    e1m4_diag_draw(e1m4_diag_window_mask, e1m4_diag_rejects);
    return;
    #ifdef DEBUG_PORTAL_CLIP""")

    draw_code = r"""
/* E1M4 trace only. Covers ONLY yclip-open spans, without changing yclip.
   A returned portal may be legitimately occluded or later drawn by another
   branch: the coloured cells indicate a correlation, not causality.
   Each 16-bit word represents 4 packed 4bpp pixels in a framebuffer column.
   If no reject occurred, open space is displayed as 0xEEEE; otherwise:
     0x1111 depth; 0x3333 active/cycle; 0x5555 revisit;
     0x7777 origin guard; 0xBBBB stack guard; 0x9999 mixed causes.
   A 2-row stripe at the TOP marks returned windows even if covered;
   first 4 groups of 8 columns are a live presence indicator by cause. */
void e1m4_diag_draw(const u8* masks, const volatile u16* counts) {
    for (u16 x=0; x<RENDER_WIDTH; x++) {
        u8 mask = masks[x];
        u16 v = 0xEEEE;
        if (mask) {
            if (mask & (mask-1)) v = 0x9999;
            else if (mask & 1) v = 0x1111;
            else if (mask & 2) v = 0x3333;
            else if (mask & 4) v = 0x5555;
            else if (mask & 8) v = 0x7777;
            else v = 0xBBBB;
        }
        u16* dst = (u16*)(bmp_buffer_write + buf_column_offset_table[x]);
        u8 lo = yclip[x<<1], hi = yclip[(x<<1)+1];
        if (hi > SCREEN_HEIGHT) hi = SCREEN_HEIGHT;
        for (u16 y=lo; y<hi; y++) dst[y] = v;
        /* Mark returned horizontal windows at the top, including those
           that later become covered. This is not a surface depth mask. */
        if (mask) dst[0] = v;
    }
    const u16 legend[5] = {0x1111,0x3333,0x5555,0x7777,0xBBBB};
    for (u16 i=0; i<5; i++) {
        if (!counts[i]) continue;
        for (u16 x=1+i*8; x<7+i*8; x++) {
            u16* dst=(u16*)(bmp_buffer_write + buf_column_offset_table[x]);
            dst[1] = legend[i];
            dst[2] = legend[i];
        }
    }
}
"""
    p = draw.read_text()
    if "void e1m4_diag_draw(" in p:
        raise RuntimeError("trace already applied to draw.c")
    draw.write_text(p + "\n" + draw_code)


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--tree", type=Path, required=True)
    a.add_argument("--mode", choices=["control","trace","depth48","revisit12","both"], required=True)
    x = a.parse_args()
    src = x.tree / "src"
    portal = src / "portal.c"
    if not portal.is_file() or not (src/"draw.c").is_file():
        raise SystemExit("Missing staged Manifold portal.c / draw.c")

    if x.mode in ("depth48", "both"):
        replace_exact(portal, "#define MAX_DEPTH 32", "#define MAX_DEPTH 48")
    if x.mode in ("revisit12", "both"):
        replace_exact(portal,
            "if(sector_rendered_cache[sector] >= 10)",
            "if(sector_rendered_cache[sector] >= 24)")
    if x.mode == "trace":
        apply_trace(src)
    print(f"E1M4_DIAG_PATCH_OK mode={x.mode} path={x.tree}")


if __name__ == "__main__":
    main()
