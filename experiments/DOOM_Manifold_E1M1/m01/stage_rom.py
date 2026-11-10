#!/usr/bin/env python3
"""Stage a disposable Manifold candidate with an E1M1 portal_map.

NOT an acceptance claim. Runs after source audit and emission gate; only
writes to --out directory. The R128/Sega CD build tree is never modified.
"""
from __future__ import annotations
import os
import argparse
import json
from pathlib import Path
import re
import shutil
from bootstrap import UPSTREAM, PIN
from convert_wad import read_map
from emit_portal_map import candidate, emit, nodes_from_wad

def point_inside(poly,p):
    # Convex point-in-polygon, accommodating either winding.
    signs=[]
    for i,(x,y) in enumerate(poly):
        nx,ny=poly[(i+1)%len(poly)]
        z=(nx-x)*(p[1]-y)-(ny-y)*(p[0]-x)
        if abs(z)>1:
            signs.append(z>0)
    return not signs or all(v==signs[0] for v in signs)

def stage_missing_resources(out):
    """Generate neutral 4bpp indexed PNGs and reuse valid public sample WAVs.

    Upstream's .res manifest references files absent from its own repository.
    Generated assets exist only inside the disposable working directory.
    """
    import struct
    import zlib
    def png(path,w,h):
        # PNG indexed (palette size=16), palette slot 0 transparent/black.
        def chunk(typ,payload):
            body=typ+payload
            return struct.pack(">I",len(payload))+body+struct.pack(">I",zlib.crc32(body)&0xffffffff)
        ihdr=struct.pack(">IIBBBBB",w,h,8,3,0,0,0)
        pal=bytes(i*12 for i in range(16) for _ in range(3))
        pixels=bytearray()
        for y in range(h):
            pixels.append(0)
            pixels.extend(1+((x//8+y//8)%3) for x in range(w))
        data=(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",ihdr)
              +chunk(b"PLTE",pal)+chunk(b"IDAT",zlib.compress(bytes(pixels)))
              +chunk(b"IEND",b""))
        path.write_bytes(data)
    required={
        "images/green_key_inv.png":(32,32),
        "images/red_key_inv.png":(32,32),
        "images/pause_checker.png":(16,16),
        "images/SHOTGUN_RELOAD.png":(64,128),
        "images/SMILE.png":(16,16),
        "images/FROWN.png":(16,16),
    }
    for file,(w,h) in required.items():
        dest=out/"res"/file
        if not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            png(dest,w,h)
    sample=out/"res/sfx/select.wav"
    if not sample.exists():
        raise ValueError("Upstream valid WAV sample is missing")
    for file in ["shotgun.wav","jump1.wav","jump2.wav",
                 "liftgoup.wav","enemya_wake.wav"]:
        dest=out/"res/sfx"/file
        if not dest.exists():
            shutil.copyfile(sample,dest)

def normalize_legacy_asm(out):
    """Legacy Manifold 68k .s uses '|' trailing comments rejected by our GAS.

    Strip comments on the two authored .s files; never modify SGDK or the
    original upstream checkout. Validate source still contains instructions.
    """
    for path in (out/"src").rglob("*.s"):
        filename=str(path.relative_to(out/"src"))
        source=path.read_text()
        filtered="\n".join(line.split("|",1)[0].rstrip()
                              for line in source.splitlines())+"\n"
        if not filtered.strip() or len(filtered)>len(source):
            raise ValueError(f"unexpected ASM comment conversion: {filename}")
        path.write_text(filtered)

def namespace_legacy_allocators(out):
    """Avoid collision between upstream two-argument malloc/free and SGDK macros."""
    import re
    for p in (out/"src").rglob("*"):
        if p.is_file() and p.suffix in (".c",".h"):
            source=p.read_text()
            changed=re.sub(r"\b(malloc|free)(\s*\()",lambda m:"man_"+m.group(1)+m.group(2),source)
            if changed!=source:
                p.write_text(changed)

def normalize_legacy_s16_bounds(out):
    """Resolve legacy Manifold s16 extrema absent in installed SGDK headers.

    Patch only the disposable renderer source, without changing its algorithm.
    Fail closed if upstream stops using the expected expressions.
    """
    p=out/"src/bunch_render.c"
    source=p.read_text()
    if "MAX_S16" not in source or "MIN_S16" not in source:
        raise ValueError("legacy s16 bounds not found in expected renderer")
    p.write_text(source.replace("MAX_S16","32767").replace("MIN_S16","(-32768)"))

def normalize_legacy_fixed_point_api(out):
    """Translate SGDK deprecated legacy fixed-point spellings to current API.

    Only patch the isolated candidate. Preserve fixed-point types and scaling.
    """
    replacements = {
        "fix32Mul": "F32_mul",
        "fix32ToInt": "F32_toInt",
        "fix32ToFix16": "F32_toFix16",
        "intToFix32": "FIX32",
    }
    import re
    counts = {k: 0 for k in replacements}
    for p in (out/"src").rglob("*"):
        if not p.is_file() or p.suffix not in (".c", ".h"):
            continue
        original = p.read_text()
        updated = original
        for old, new in replacements.items():
            pattern = r"\b" + old + r"(?=\s*\()"
            updated, n = re.subn(pattern, new, updated)
            counts[old] += n
        if updated != original:
            p.write_text(updated)
    if not counts["fix32Mul"] or not counts["intToFix32"]:
        raise ValueError(f"legacy fixed-point API signatures changed: {counts}")
    print("Legacy SGDK fixed-point API rewrites:", counts)

def normalize_wide_sprite_registers(out):
    """Restore missing pointer types in upstream's wide sprite ASM bridge."""
    p=out/"src/draw.c"
    s=p.read_text()
    old0='register const a0 asm ("%a0") = (u32)cur_texel_ptr;'
    old1='register const a1 asm ("%a1") = (u32)cur_column_ptr;'
    if s.count(old0)!=1 or s.count(old1)!=1:
        raise ValueError("upstream wide sprite register bridge changed")
    s=s.replace(old0,'register const u8* a0 asm ("%a0") = cur_texel_ptr;')
    s=s.replace(old1,'register const u8* a1 asm ("%a1") = cur_column_ptr;')
    p.write_text(s)

def normalize_legacy_palette_and_asm(out):
    """Match current palette API and constrain arithmetic ASM operands to Dn."""
    fire=out/"src/fire.c"
    data=fire.read_text()
    old="PAL_setPalette(PAL1, fire_cols);"
    if data.count(old)!=1:
        raise ValueError("Manifold fire palette invocation changed")
    fire.write_text(data.replace(old,"PAL_setPalette(PAL1, fire_cols, DMA);"))
    draw=out/"src/draw.c"
    data=draw.read_text()
    old=': "+a" (tex_col_ptr), "+r" (u_11_start), "+r" (u_11_tmp), "+r" (one_over_z_16)'
    new=': "+a" (tex_col_ptr), "+r" (u_11_start), "+d" (u_11_tmp), "+r" (one_over_z_16)'
    if data.count(old)!=1:
        raise ValueError("Manifold horizontal texture ASM constraint changed")
    draw.write_text(data.replace(old,new))

def normalize_game_integration(out):
    """Correct stale upstream game calls and SGDK palette transfer signatures."""
    p=out/"src/game.c"
    source=p.read_text()
    rewrites={
        "showStats(0);":"showStats();",
        "step_weapon_animation();":"step_weapon_animation(DMA_QUEUE);",
        "void return_to_menu() {":"void return_to_menu(int menu_idx) {",
        "volatile u32* vp_init_load_level_arr = instant_load_level_array;":
          "volatile const int* vp_init_load_level_arr = instant_load_level_array;",
        "init_shotgun(free_tile_loc);":"init_shotgun();",
    }
    for old,new in rewrites.items():
        if source.count(old)!=1:
            raise ValueError(f"Manifold game signature changed: {old}")
        source=source.replace(old,new)
    import re
    source,n=re.subn(r"PAL_setPalette\((PAL[0-3]),\s*([^();]+)\);",
                      r"PAL_setPalette(\1, \2, DMA);",source)
    if n!=6:
        raise ValueError(f"unexpected Manifold game palette call count {n}")
    p.write_text(source)

def normalize_weapon_api_declaration(out):
    """Match weapon header declaration to upstream implementation name."""
    p=out/"src/weapon_sprites.h"
    data=p.read_text()
    old="void step_weapon_anim(TransferMethod transfer_type);"
    if data.count(old)!=1:
        raise ValueError("upstream weapon step declaration changed")
    p.write_text(data.replace(old,"void step_weapon_animation(TransferMethod transfer_type);"))

def normalize_remaining_palettes(out):
    """Adapt other upstream PAL_setPalette calls that omit TransferMethod."""
    import re
    count=0
    for p in (out/"src").rglob("*.c"):
        data=p.read_text()
        lines=data.splitlines(keepends=True)
        for i,line in enumerate(lines):
            match=re.search(r"PAL_setPalette\(PAL[0-3],\s*[^,();]+\);",line)
            if match:
                call=match.group()
                lines[i]=line.replace(call,call[:-2]+", DMA);")
                count+=1
        if data!="".join(lines):
            p.write_text("".join(lines))
    if count<1:
        raise ValueError("expected at least one extra legacy palette API call")
    print("Other SGDK PAL API calls normalized:",count)

def normalize_menu_callbacks(out):
    """Use type-correct wrappers for callbacks accepting selected menu index."""
    p=out/"src/main_menu.c"
    src=p.read_text()
    old='#include "music.h"'
    if src.count(old)!=1:
        raise ValueError("main menu insertion anchor changed")
    src=src.replace(old,old+"""
static void select_toggle_sfx(int menu_idx) { (void)menu_idx; toggle_sfx(); }
static void select_toggle_music(int menu_idx) { (void)menu_idx; toggle_music(); }
static void select_toggle_dither(int menu_idx) { (void)menu_idx; toggle_dither_mode(); }
""")
    replacements={
        "void go_to_new_game() {":"void go_to_new_game(int menu_idx) {",
        "void populate_level_select() {":"void populate_level_select(int menu_idx) {",
        ".select = &toggle_sfx":".select = &select_toggle_sfx",
        ".select = &toggle_music":".select = &select_toggle_music",
        ".select = &toggle_dither_mode":".select = &select_toggle_dither",
    }
    for old,new in replacements.items():
        if src.count(old)!=1:
            raise ValueError(f"main menu callback changed: {old}")
        src=src.replace(old,new)
    p.write_text(src)

def normalize_math_and_menu(out):
    """Fix vector array pointer scaling and obsolete clear_menu argument."""
    p=out/"src/math3d.c"
    src=p.read_text()
    old="s16* last_out_ptr = out + (num_walls*2);"
    if src.count(old)!=1:
        raise ValueError("upstream vector pointer arithmetic changed")
    # out is Vect2D_s16* (4 bytes): upstream advanced by num_walls*2 VECTORS
    # (8 bytes/wall, the loop writes 4 words per wall backwards). Casting
    # before adding halves the offset and smashes memory below `out`, so
    # every sector transformed garbage and nothing was drawn. Cast after.
    p.write_text(src.replace(old,"s16* last_out_ptr = (s16*)(out + (num_walls*2));"))
    p=out/"src/menu_helper.c"
    src=p.read_text()
    if src.count("clear_menu(cur_menu);")!=2:
        raise ValueError("upstream obsolete menu-clear calls changed")
    p.write_text(src.replace("clear_menu(cur_menu);","clear_menu();"))

def normalize_bitmap_legacy_symbols(out):
    """Compatibility spellings for the copied SGDK bitmap engine.

    These are token-level renames preserving tile counts and VRAM byte offsets.
    """
    p=out/"src/my_bmp.c"
    source=p.read_text()
    tokens={
        "BMP_PLANWIDTH":"BMP_PLANE_WIDTH",
        "BMP_PLANHEIGHT":"BMP_PLANE_HEIGHT",
        "BMP_CELLWIDTH":"BMP_TILE_WIDTH",
        "BMP_CELLHEIGHT":"BMP_TILE_HEIGHT",
        "BMP_CELLXOFFSET":"BMP_TILE_XOFFSET",
        "BMP_CELLYOFFSET":"BMP_TILE_YOFFSET",
        "BMP_BASETILEINDEX":"BMP_BASE_TILE_INDEX",
        "BMP_FB0TILEINDEX":"BMP_FB0_TILE_INDEX",
        "BMP_FB1TILEINDEX":"BMP_FB1_TILE_INDEX",
        "BMP_FB0TILE":"BMP_FB0_ADDR",
        "BMP_FB1TILE":"BMP_FB1_ADDR",
        "GFX_CTRL_PORT":"VDP_CTRL_PORT",
        "GFX_DATA_PORT":"VDP_DATA_PORT",
        "GFX_WRITE_VRAM_ADDR":"VDP_WRITE_VRAM_ADDR",
        "IS_PALSYSTEM":"IS_PAL_SYSTEM",
    }
    import re
    count=0
    for old,new in tokens.items():
        source,n=re.subn(r"\b"+old+r"\b",new,source)
        count+=n
    if count<30:
        raise ValueError(f"unexpected bitmap compatibility rewrite count {count}")
    p.write_text(source)
    print("Legacy bitmap API symbols normalized:",count)

def normalize_pvs_entry_types(out):
    """Read PVS and PHS run-length streams as the actual signed bytes."""
    p=out/"src/portal_map.c"
    src=p.read_text()
    replacements={
        "sector_in_pvs_inner(u16 check_sector, s8* entries_for_src_sector)":
          "sector_in_pvs_inner(u16 check_sector, const s8* entries_for_src_sector)",
        "s8* entries = &mp->sector_pvs_entries[pvs_offset];":
          "const s8* entries = &mp->sector_pvs_entries[pvs_offset];",
        "s16* entries = &mp->sector_phs_entries[phs_offset];":
          "const s8* entries = &mp->sector_phs_entries[phs_offset];",
    }
    for old,new in replacements.items():
        expected = 2 if old == "s8* entries = &mp->sector_pvs_entries[pvs_offset];" else 1
        if src.count(old)!=expected:
            raise ValueError(f"upstream PVS stream changed: {old}")
        src=src.replace(old,new)
    p.write_text(src)

def normalize_toggle_declarations(out):
    """Correct header prototypes to match existing sfx/music callback definitions."""
    for file,old,new in (
        ("sfx.h","void toggle_sfx();","void toggle_sfx(int menu_idx);"),
        ("music.h","void toggle_music();","void toggle_music(int menu_idx);"),
    ):
        p=out/"src"/file
        source=p.read_text()
        if source.count(old)!=1:
            raise ValueError(f"upstream toggle prototype changed: {file}")
        p.write_text(source.replace(old,new))
    p=out/"src/main_menu.c"
    source=p.read_text()
    for old,new in (
        ("(void)menu_idx; toggle_sfx();","toggle_sfx(menu_idx);"),
        ("(void)menu_idx; toggle_music();","toggle_music(menu_idx);"),
    ):
        if source.count(old)!=1:
            raise ValueError(f"menu toggle wrapper changed: {old}")
        source=source.replace(old,new)
    p.write_text(source)

def normalize_weapon_sprite_frame_layout(out):
    """Use current SGDK inline FrameVDPSprite records instead of retired pointers."""
    p=out/"src/weapon_sprites.c"
    src=p.read_text()
    for old,new,n in (
        ("FrameVDPSprite** f = frame->frameInfos[0].frameVDPSprites;",
         "FrameVDPSprite* f = frame->frameVDPSprites;",1),
        ("FrameVDPSprite** f = frame1->frameInfos[0].frameVDPSprites;",
         "FrameVDPSprite* f = frame1->frameVDPSprites;",1),
        ("FrameVDPSprite* spr = f[i];","FrameVDPSprite* spr = &f[i];",2),
    ):
        if src.count(old)!=n:
            raise ValueError(f"SGDK weapon sprite layout changed: {old}")
        src=src.replace(old,new)
    p.write_text(src)

def normalize_header_global_definitions(out):
    """Make global data declarations extern; retain one definition per TU."""
    patches={
        "obj_sprite.h":[
            ("const u32 scaled_sprite_run_lengths[64*513];",
             "extern const u32 scaled_sprite_run_lengths[64*513];"),
            ("const u32 scaled_sprite_texel_per_pixel_lut[513];",
             "extern const u32 scaled_sprite_texel_per_pixel_lut[513];"),
            ("const u16* const sprite_scale_coefficients_pointer_lut[513];",
             "extern const u16* const sprite_scale_coefficients_pointer_lut[513];"),
        ],
        "clip_buf.h":[("clip_buf* clip_buffers;","extern clip_buf* clip_buffers;")],
        "portal.h":[("u8* sector_rendered_cache;","extern u8* sector_rendered_cache;")],
        "map_table.h":[("const uint32_t map_table[MAX_MAPS+2];",
                        "extern const uint32_t map_table[MAX_MAPS+2];")],
    }
    for filename,replacements in patches.items():
        p=out/"src"/filename
        data=p.read_text()
        for old,new in replacements:
            if data.count(old)!=1:
                raise ValueError(f"unexpected header definition: {filename}, {old}")
            data=data.replace(old,new)
        p.write_text(data)
    # The copied bitmap engine and SGDK BMP both declare bmp_plane_addr.
    # Keep independent state names, since they are distinct implementations.
    p=out/"src/my_bmp.c"
    data=p.read_text()
    if data.count("bmp_plane_addr")<2:
        raise ValueError("missing custom bitmap plane state")
    import re
    p.write_text(re.sub(r"\bbmp_plane_addr\b","manifold_bmp_plane_addr",data))

def mute_legacy_emulator_debug_logging(out):
    """Avoid invoking old SGDK KLog emulator debug traps in release candidates.

    Legacy KLog calls can enter BlastEm's debugger without a terminal, making
    a healthy boot appear frozen. This alters only isolated staged sources.
    """
    base=out/"src"
    definitions="#include <genesis.h>\n"
    names=("KLog","KLog_U1","KLog_U2","KLog_U3","KLog_U4",
           "KLog_U1_","KLog_U2_","KLog_U3_","KLog_U4_",
           "KLog_U1x","KLog_U2x","KLog_U3x","KLog_U4x")
    for name in names:
        definitions+=f"#define {name}(...) ((void)0)\n"
    (base/"manifold_mute_klog.h").write_text(definitions)
    count=0
    for c in base.glob("*.c"):
        code=c.read_text()
        c.write_text('#include "manifold_mute_klog.h"\n'+code)
        count+=1
    print("Legacy emulator debug log calls suppressed in",count,"C units")

def fix_sgdk2_hint_callbacks(out):
    """SGDK 2.x H-Int vector is `hintCaller: JMP callback.L` (sys.c).

    The callback is entered directly from the exception, so it must save
    every register it uses and return with RTE. Manifold's bitmap H-Int
    handlers were plain C functions (RTS, d0/d1/a0/a1 clobbered): returning
    pops SR+PC as a PC, misaligns SSP by 2 and lands on random/odd code,
    matching the ADDRESS ERROR with Hint=bmp_do_hblank_process_vertical.
    """
    p=out/"src/my_bmp.c"
    s=p.read_text()
    for name in ("bmp_do_hblank_process_vertical","bmp_do_hblank_process_horizontal"):
        old=f"void {name}() {{"
        if s.count(old)!=1:
            raise ValueError(f"H-Int handler definition changed: {name}")
        s=s.replace(old,f"HINTERRUPT_CALLBACK {name}() {{")
    p.write_text(s)
    print("H-Int bitmap handlers now __attribute__((interrupt)) (RTE, full save)")

def _asm_blocks(s):
    import re
    for m in re.finditer(r'__asm\s*(?:volatile|__volatile__)?\s*\(',s):
        i=m.end();d=1;instr=False
        while d:
            c=s[i]
            if instr:
                if c=='\\': i+=1
                elif c=='"': instr=False
            else:
                if c=='"': instr=True
                elif c=='(': d+=1
                elif c==')': d-=1
            i+=1
        yield m.end(),i-1

def _split_asm_sections(body):
    parts=[];cur='';instr=False;d=0;i=0
    while i<len(body):
        c=body[i]
        if instr:
            cur+=c
            if c=='\\': cur+=body[i+1]; i+=1
            elif c=='"': instr=False
        else:
            if c=='"': instr=True
            elif c=='(': d+=1
            elif c==')': d-=1
            if c==':' and d==0:
                parts.append(cur); cur=''; i+=1; continue
            cur+=c
        i+=1
    parts.append(cur)
    return parts

def _asm_operands(section):
    import re
    clean=re.sub(r'//[^\n]*','',section).replace('\\\n',' ')
    return [(c,e.strip()) for c,e in re.findall(r'"([^"]*)"\s*\(([^()]*)\)',clean)]

def fail_loud_on_heap_exhaustion(out):
    """Upstream malloc wrapper returned MEM_alloc's NULL unchecked.

    Under SGDK 2.x (bigger system RAM reservation) a NULL here makes object
    lists/bitmap buffers alias ROM at 0x000000: reads return vector bytes,
    so linked lists cycle forever (MAME hang in process_objects_in_sector).
    Stop with an on-screen message instead of corrupting state.
    """
    p=out/"src/utils.c"
    s=p.read_text()
    old="    void* p = MEM_alloc(size);\n"
    if s.count(old)!=1:
        raise ValueError("upstream malloc wrapper changed")
    s=s.replace(old,old+"""    if (p == NULL) {
        static char oom[80];
        sprintf(oom, "OOM %s %u B, heap free %u", thing, size, MEM_getFree());
        SYS_die(oom);
    }
""")
    p.write_text(s)
    print("Heap exhaustion now fails loudly via SYS_die")

MAX_WALLS_PER_SECTOR=255
def widen_sector_vertex_buffers(out):
    """portal.c keeps per-sector transformed vertices on the stack in
    `Vect2D_s16 buf[62]`, and load_transform_and_duplicate_verts writes
    2 entries per wall: upstream maps never exceed 30 walls per sector,
    E1M1 BSP cells do -> stack smash. Size for MAX_WALLS_PER_SECTOR."""
    p=out/"src/portal.c"
    s=p.read_text()
    n=2*MAX_WALLS_PER_SECTOR+4
    count=0
    for name in ("transformed_vert_buffer","transformed_vertex_buffer"):
        old=f"Vect2D_s16 {name}[62];"
        c=s.count(old)
        s=s.replace(old,f"Vect2D_s16 {name}[{n}];")
        count+=c
    if count!=2:
        raise ValueError(f"expected 2 per-sector vertex buffers, got {count}")
    p.write_text(s)
    print("Per-sector vertex stack buffers widened to",n,"entries")

def relocate_free_tiles_after_sgdk2_framebuffer(out):
    """Manifold hardcodes free_tile_loc = 0x390 = 16 + 896 framebuffer tiles,
    i.e. SGDK 1.x TILE_USERINDEX=16. SGDK 2.x puts the font first
    (TILE_USER_INDEX = 112), so the double framebuffer spans up to 0x3F0 and
    the game zeroed/overwrote tiles 0x390..0x3F0 inside it (black bands,
    missing weapon). Start game tiles after the real framebuffer and stop
    before the H-scroll table (0xA800 -> tile 0x540)."""
    p=out/"src/game.c"
    s=p.read_text()
    reps={
        "    free_tile_loc = 0x390;\n":
        "    free_tile_loc = MANIFOLD_FREE_TILE_BASE;\n",
        "    VDP_fillTileData(0x00, 0x0390, 0x170, 1);\n":
        "    VDP_fillTileData(0x00, MANIFOLD_FREE_TILE_BASE, MANIFOLD_FREE_TILE_LIMIT - MANIFOLD_FREE_TILE_BASE, 1);\n",
        "    free_tile_loc = console_init(free_tile_loc);\n":
        "    free_tile_loc = console_init(free_tile_loc);\n"
        "    if (free_tile_loc > MANIFOLD_FREE_TILE_LIMIT) {\n"
        "        static char vram_msg[48];\n"
        "        sprintf(vram_msg, \"VRAM tiles %X > %X\", free_tile_loc, MANIFOLD_FREE_TILE_LIMIT);\n"
        "        SYS_die(vram_msg);\n"
        "    }\n",
    }
    for old,new in reps.items():
        if s.count(old)!=1:
            raise ValueError(f"game.c tile layout changed: {old!r}")
        s=s.replace(old,new)
    s=("#include <genesis.h>\n"
       "#define MANIFOLD_FREE_TILE_BASE (TILE_USER_INDEX + 32*20/2 + 32*18)\n"
       "#define MANIFOLD_FREE_TILE_LIMIT 0x540\n")+s
    p.write_text(s)
    print("Game tiles relocated after SGDK2 framebuffer (TILE_USER_INDEX+896)")

def harden_inline_asm(out, files=("draw.c","math3d.c","utils.c","vwf.c","bunch_render.c")):
    """Make upstream GCC-6-era inline asm legal for GCC 13/15 -O3.

    1. Input operands the template writes (dy scratch, `addq.l #1,%2`,
       zero-initialised temporaries) become "+" outputs, renumbering %N.
       Writing an input is undefined: newer GCC shares that register with
       other live values, silently corrupting pointers/loop counters.
    2. Every block gets "cc" and "memory" clobbers (they store through
       (%0)+ and JSR into generated code without telling the compiler).
    Fail closed on unparsable blocks.
    """
    import re
    written=re.compile(r'^\s*(?:(neg|not|ext|swap|clr)\S*\s+%(\d+)\b|(?!cmp|tst|btst)\w+(?:\.\w)?\s+.*,\s*%(\d+)\s*$)')
    total_promoted=0;total_blocks=0
    for f in files:
        p=out/"src"/f
        s=p.read_text()
        edits=[]
        for b,e in _asm_blocks(s):
            line_start=s.rfind("\n",0,b)+1
            if s[line_start:b].lstrip().startswith("//"):
                continue  # commented-out upstream experiment
            body=s[b:e]
            parts=_split_asm_sections(body)
            if len(parts)==1:
                continue  # basic asm, no operands
            total_blocks+=1
            tmpl_src=parts[0]
            tmpl=''.join(re.findall(r'"((?:[^"\\]|\\.)*)"',tmpl_src,re.S)).replace('\\\n','')
            outs=_asm_operands(parts[1])
            ins=_asm_operands(parts[2]) if len(parts)>2 else []
            clob=parts[3] if len(parts)>3 else ''
            n=len(outs)
            promote=set()
            for line in re.split(r'\\t\\n|\\n|;',tmpl):
                line=line.split('|')[0]
                m=written.match(line)
                if m:
                    idx=int(m.group(2) or m.group(3))
                    if idx>=n: promote.add(idx-n)
            if promote:
                bad=[ins[k] for k in promote if not re.fullmatch(r'[A-Za-z_]\w*',ins[k][1])]
                if bad:
                    raise ValueError(f"{f}: cannot promote non-lvalue asm inputs {bad}")
                new_outs=outs+[("+"+ins[k][0].lstrip("=+&"),ins[k][1]) for k in sorted(promote)]
                kept=[k for k in range(len(ins)) if k not in promote]
                mapping={i:i for i in range(n)}
                for j,k in enumerate(sorted(promote)): mapping[n+k]=n+j
                for j,k in enumerate(kept): mapping[n+k]=len(new_outs)+j
                tmpl_src=re.sub(r'(?<!%)%(\d+)',lambda m:'%'+str(mapping[int(m.group(1))]),tmpl_src)
                outs=new_outs; ins=[ins[k] for k in kept]
                total_promoted+=len(promote)
            cl=[c.strip() for c in re.findall(r'"([^"]*)"',clob)]
            for c in ("cc","memory"):
                if c not in cl: cl.append(c)
            fmt=lambda L:", ".join(f'"{c}" ({e})' for c,e in L)
            nl="\\\n" if '\\\n' in body else "\n"   # macro continuation
            head=tmpl_src.rstrip()
            if head.endswith("\\"): head=head[:-1].rstrip()
            new_body=(head+nl+"        : "+fmt(outs)+nl+"        : "+fmt(ins)
                      +nl+"        : "+", ".join(f'"{c}"' for c in cl)+nl+"    ")
            edits.append((b,e,new_body))
        for b,e,nb in reversed(edits):
            s=s[:b]+nb+s[e:]
        # promoted register-asm locals must be writable
        s=s.replace('register const u8* a1 asm ("%a1")','register u8* a1 asm ("%a1")')
        p.write_text(s)
    if total_blocks<60 or total_promoted<8:
        raise ValueError(f"unexpected asm hardening counts blocks={total_blocks} promoted={total_promoted}")
    print(f"Inline asm hardened: {total_blocks} blocks, {total_promoted} written inputs promoted")

def replace_generated_vertical_scalers_with_checked_c(out):
    """Diagnostic: remove computed jumps into 512 generated 68000 scaler routines.

    Screenshot Address 0x08001D (accessed address, not proven PC) lands one byte before scale_64_450_jump
    (0x08001E); the corresponding entry is scale_64_450_bot_clip
    (0x080004). Invalid parameters or registers must never reach it.
    Use simple, bounded, equivalent nearest-neighbor C pixel writes until
    the original 68k register constraints and clip values are audited.
    """
    p=out/"src/texture.c"
    source=p.read_text()
    replacements={
        "draw_texture_vertical_line": """
void draw_texture_vertical_line(s16 unclipped_y0, u16 y0, s16 unclipped_y1,
                                u8* col_ptr, const u16* tex_column) {
    s32 full=(s32)unclipped_y1-(s32)unclipped_y0;
    if (!col_ptr || !tex_column || full<=0 || full>512 || y0>=144) return;
    if (((u32)col_ptr & 1) || ((u32)tex_column & 1)) return;
    s32 start=(s32)y0-(s32)unclipped_y0;
    if (start<0 || start>=full) return;
    u16* dst=(u16*)col_ptr;
    s32 visible=full-start;
    if (visible>144-(s32)y0) visible=144-(s32)y0;
    u32 step=(64UL<<16)/(u32)full;
    u32 u=(u32)start*step;
    dst+=y0;
    for (s32 i=0; i<visible; ++i) {
        u16 t=(u16)(u>>16);
        *dst++ = tex_column[t>63?63:t];
        u+=step;
    }
}
""",
        "draw_bottom_clipped_texture_vertical_line": """
void draw_bottom_clipped_texture_vertical_line(s16 unclipped_y0, u16 y0,
                                                s16 unclipped_y1, u16 y1,
                                                u8* col_ptr, const u16* tex_column) {
    s32 full=(s32)unclipped_y1-(s32)unclipped_y0;
    if (!col_ptr || !tex_column || full<=0 || full>512 || y0>=144 || y1<=y0) return;
    if (((u32)col_ptr & 1) || ((u32)tex_column & 1)) return;
    s32 start=(s32)y0-(s32)unclipped_y0;
    if (start<0 || start>=full) return;
    s32 visible=(s32)y1-(s32)y0;
    if (visible>full-start) visible=full-start;
    if (visible>144-(s32)y0) visible=144-(s32)y0;
    u16* dst=(u16*)col_ptr;
    u32 step=(64UL<<16)/(u32)full;
    u32 u=(u32)start*step;
    dst+=y0;
    for (s32 i=0; i<visible; ++i) {
        u16 t=(u16)(u>>16);
        *dst++ = tex_column[t>63?63:t];
        u+=step;
    }
}
"""
    }
    for name,replacement in replacements.items():
        import re
        matches=list(re.finditer(r"\bvoid\s+"+name+r"\s*\(",source))
        if len(matches)!=1:
            raise ValueError(f"expected one generated scaler caller {name}, got {len(matches)}")
        start=matches[0].start()
        opening=source.index("{",matches[0].end())
        depth=1
        end=opening+1
        while depth and end<len(source):
            if source[end]=="{": depth+=1
            elif source[end]=="}": depth-=1
            end+=1
        if depth:
            raise ValueError("unterminated generated texture function")
        source=source[:start]+replacement+source[end:]
    p.write_text(source)
    print("Using bounded C fallbacks; NO generated vertical-scaler calls")

def stage(src, wad, out, control=False):
    out=out.resolve()
    if out.exists():
        raise ValueError("destination already exists: "+str(out))
    shutil.copytree(src,out,ignore=shutil.ignore_patterns(".git","out","__pycache__"))
    skip=set(filter(None,os.environ.get('MANIFOLD_SKIP','').split(',')))
    for step in (stage_missing_resources,normalize_legacy_asm,namespace_legacy_allocators,normalize_legacy_s16_bounds,normalize_legacy_fixed_point_api,normalize_wide_sprite_registers,normalize_legacy_palette_and_asm,normalize_game_integration,normalize_weapon_api_declaration,normalize_remaining_palettes,normalize_menu_callbacks,normalize_math_and_menu,normalize_bitmap_legacy_symbols,normalize_pvs_entry_types,normalize_toggle_declarations,normalize_weapon_sprite_frame_layout,normalize_header_global_definitions,mute_legacy_emulator_debug_logging,replace_generated_vertical_scalers_with_checked_c,fix_sgdk2_hint_callbacks,harden_inline_asm,fail_loud_on_heap_exhaustion,widen_sector_vertex_buffers,relocate_free_tiles_after_sgdk2_framebuffer,):
        if step.__name__ in skip:
            print('SKIPPED stage step:',step.__name__); continue
        step(out)
    # Use SGDK standard Sega boot/header instead of upstream custom startup
    # that requires an unpublished out/rom_head.bin at assembler time.
    # The upstream Python-generated demo E1M1 is superseded by src/e1m1_map.c.
    (out/"src/python/e1m1.c").unlink(missing_ok=True)
    for file in ("sega.s","rom_head.c"):
        (out/"src/boot"/file).unlink(missing_ok=True)
    # Boot directly into the experimental E1M1 rather than upstream's intro.
    # The intro uses a separate fire/bitmap renderer unrelated to this port.
    init=out/"src/init.c"
    init_source=init.read_text()
    old="0xFEEDBEEF,\n\t0\n"
    if init_source.count(old)!=1:
        raise ValueError("upstream start-in-game flag initializer changed")
    init.write_text(init_source.replace(old,"0xFEEDBEEF,\n\t1\n"))
    if control:
        # Engine control ROM: same compat/asm fixes, upstream test maps and
        # spawn. Separates renderer/VDP faults from E1M1 conversion faults.
        p=out/"src/level.c"
        p.write_text(p.read_text().replace("MAX_S32","2147483647"))
        p=out/"src/map_table.c"
        t=p.read_text()
        for m in ("overlapping_map","editor_test_map","building_test_map"):
            t=t.replace("&"+m+",","(uint32_t)&"+m+",")
        p.write_text(t)
        report={"source":UPSTREAM,"pin":PIN,"map":"upstream-control","control":True}
        (out.parent/"e1m1-stage.json").write_text(json.dumps(report,indent=2)+"\n")
        return report
    map_lumps=read_map(wad)
    cells, stats, missing=candidate(map_lumps,nodes_from_wad(wad),allow_gaps=True)
    # Prototype only: missing BSP cut edges are opaque and nontraversable.
    # Never synthesize an unsafe portal or mark this build geometry-validated.
    (out/"src/e1m1_map.c").write_text(emit(map_lumps,cells))
    max_walls=max(len(c["walls"]) for c in cells)
    stats=dict(stats) if isinstance(stats,dict) else {"stats":stats}
    stats["max_walls_per_cell"]=max_walls
    stats["cells_over_30_walls"]=sum(1 for c in cells if len(c["walls"])>30)
    print("E1M1 max walls per cell:",max_walls,"cells >30:",stats["cells_over_30_walls"])
    if max_walls>MAX_WALLS_PER_SECTOR:
        raise ValueError(f"cell with {max_walls} walls exceeds renderer buffer")
    # E1M1's split BSP contours have 1112 atomic walls; expand only this
    # isolated candidate's static budget, leaving upstream and R128 unchanged.
    header=out/"src/portal_map.h"
    h=header.read_text()
    old="#define MAX_WALLS        1024"
    if h.count(old)!=1:
        raise ValueError("upstream MAX_WALLS definition changed")
    header.write_text(h.replace(old,"#define MAX_WALLS        2048"))
    # Manifold's map chooser reads a fixed pointer table, not the Doom BSP.
    p=out/"src/maps.h"
    s=p.read_text()
    assert "#define MAPS_H" in s
    s=s.replace("#define MAPS_H","#define MAPS_H\n#include \"portal_map.h\"\nextern const portal_map e1m1_map;")
    p.write_text(s)
    p=out/"src/map_table.c"
    s=p.read_text()
    a=s.index("const uint32_t map_table[MAX_MAPS+2] = {")
    b=s.index("};",a)+2
    s=s[:a]+"""const uint32_t map_table[MAX_MAPS+2] = {
    0xDEADBEEF, 1, (uint32_t)&e1m1_map, 0, 0, 0, 0
};"""+s[b:]
    p.write_text(s)
    # Find the real player-1 THING; never place the camera at arbitrary BSP 0.
    spawns=[(x,y,angle) for x,y,angle,type_id,flags in map_lumps["THINGS"] if type_id==1]
    if len(spawns)!=1:
        raise ValueError(f"expected one player 1 spawn, got {len(spawns)}")
    x,y,angle=spawns[0]
    sp=[c["id"] for c in cells if point_inside([w["a"] for w in c["walls"]],(x*16,y*16))]
    if len(sp)!=1:
        raise ValueError(f"player spawn {x,y} falls in {len(sp)} BSP cells: {sp}")
    spawn_cell=sp[0]
    p=out/"src/level.c"
    s=p.read_text()
    if s.count("MAX_S32") != 1:
        raise ValueError("unexpected level distance bound")
    s=s.replace("MAX_S32","2147483647")
    expected="    const int init_player_sector = 0;"
    assert s.count(expected)==1,"Manifold player initializer changed"
    # No unconditional renderer refactor; set spawn only in this experiment.
    s=s.replace(expected,f"    const int init_player_sector = {spawn_cell};")
    old="    cur_player_pos.x = sector_0_center.x;\n    cur_player_pos.y = sector_0_center.y;"
    assert s.count(old)==1
    s=s.replace(old,f"    cur_player_pos.x = FIX32({x});\n    cur_player_pos.y = FIX32({y});")
    old="    cur_player_pos.ang = 0;"
    assert s.count(old)==1
    s=s.replace(old,f"    cur_player_pos.ang = {(angle*1024)//360};")
    p.write_text(s)
    report={
        "source":UPSTREAM,"pin":PIN,"map":"E1M1",
        "format":"Manifold portal_map C proof of concept",
        "player_spawn":{"x":x,"y":y,"doom_angle":angle,"manifold_cell":spawn_cell},
        "geometry":stats,"safe_for_runtime":not missing,
        "unpaired_edges_are_solid":len(missing),
        "renderer_unchanged":True,"lighting_color_placeholder":True,
        "thing_spawns_pending":True,"doors_triggers_pending":True
    }
    (out.parent/"e1m1-stage.json").write_text(json.dumps(report,indent=2)+"\n")
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--wad",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--control",action="store_true")
    args=ap.parse_args()
    print(json.dumps(stage(args.source,args.wad,args.out,args.control),indent=2))

if __name__=="__main__":
    main()
