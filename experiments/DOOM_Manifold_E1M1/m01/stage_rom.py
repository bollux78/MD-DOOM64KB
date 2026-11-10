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
           "KLog_U1x","KLog_U2x","KLog_U3x","KLog_U4x",
           "KLog_S1","KLog_S2","KLog_S3","KLog_S4",
           "KLog_S1_","KLog_S2_","KLog_S3_","KLog_S4_",
           "KLog_F1","KLog_F2","KLog_F3","KLog_F4",
           "KLog_f1","KLog_f2","KLog_f3","KLog_f4")
    for name in names:
        definitions+=f"#define {name}(...) ((void)0)\n"
    # MEM_dump() prints via KDebug; BlastEm opens a terminal window for it
    # and blocks when none is available (headless runner / some desktops).
    definitions+="#define MEM_dump() ((void)0)\n"
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

MAX_WALLS_PER_SECTOR=16  # E1M1 BSP cells have <=11 walls; 255 made visit_graph frames 2.3KB -> stack overflow into heap
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
       "#define MANIFOLD_FREE_TILE_LIMIT 0x500\n")+s
    p.write_text(s)
    print("Game tiles relocated after SGDK2 framebuffer (TILE_USER_INDEX+896)")

def guard_portal_recursion_stack(out):
    """visit_graph recurses once per portal hop. E1M1 chains far deeper than
    upstream maps and the stack (above the heap/framebuffers) grew down into
    the heap, corrupting object lists -> wild jump. Track the heap top in
    man_malloc and stop recursing when the stack gets close to it."""
    u=out/"src/utils.c"
    s=u.read_text()
    old="    void* p = MEM_alloc(size);\n"
    if s.count(old)!=1: raise ValueError("man_malloc changed")
    s=s.replace("void* man_malloc(u16 size, const char* thing) {","u32 manifold_heap_high = 0;\nvoid* man_malloc(u16 size, const char* thing) {",1)
    s=s.replace(old,old+"    if (p && ((u32)p + size) > manifold_heap_high) { manifold_heap_high = (u32)p + size; }\n",1)
    u.write_text(s)
    p=out/"src/portal.c"
    s=p.read_text()
    old="void visit_graph(u16 src_sector, u16 sector, u16 x1, u16 x2, u32 cur_frame, uint8_t depth) {"
    if s.count(old)!=1: raise ValueError("visit_graph signature changed")
    s=s.replace(old,"extern u32 manifold_heap_high;\nextern volatile u32 manifold_dbg[8];\nvolatile u32 manifold_dbg_maxdepth;\n"+old+"""
    {
        u32 sp_now;
        __asm volatile("move.l %%sp,%0" : "=d" (sp_now));
        if (depth > 48 || (sp_now & 0xFFFFFF) < ((manifold_heap_high & 0xFFFFFF) + 3072)) { manifold_dbg[7]++; return; }
        if (depth > manifold_dbg_maxdepth) { manifold_dbg_maxdepth = depth; }
    }""",1)
    p.write_text(s)
    print("portal recursion bounded by stack/heap guard")

def robust_sector_crossing(out):
    """Upstream collision lets the player cross a portal line even when the
    new point is not inside the neighbour (corner cut into a 3rd cell); the
    player then sits outside its sector and walks through walls into void.
    Search the neighbour's neighbours; if still not found, block the move."""
    p=out/"src/collision.c"
    s=p.read_text()
    helper="""
static s16 manifold_locate2(fix32 x, fix32 y, s16 sect) {
    portal_map* mp = (portal_map*)cur_portal_map;
    u16 n = sector_num_walls(sect, mp);
    u16 po = sector_portal_offset(sect, mp);
    for (u16 i = 0; i < n; i++) {
        s16 d = mp->portals[po + i];
        if (d >= 0 && within_sector(x, y, d)) { return d; }
    }
    return -1;
}
"""
    anchor="f32 sq_shortest_dist_to_point("
    if s.count(anchor)!=1: raise ValueError("collision layout changed")
    s=s.replace(anchor,helper+anchor,1)
    for axis,args,pos in (("x","newx, cury","curx = newx;"),("y","curx, newy","cury = newy;")):
        old=f"""                }} else {{
                    //KLog("{axis} moved over line but not blocked or in sector, stay in current sector");
                    continue;
                }}"""
        new=f"""                }} else {{
                    s16 found = manifold_locate2({args}, portal_sect);
                    if (found >= 0) {{ cur_sector = found; {pos} break; }}
                    crossed_line_{axis} = 1;
                    continue;
                }}"""
        if s.count(old)!=1: raise ValueError(f"{axis} crossing branch changed")
        s=s.replace(old,new,1)
    # final validation: never leave the player outside its claimed cell
    sig="collision_result check_for_collision_radius(fix32 curx, fix32 cury, fix32 cur_z, fix32 newx, fix32 newy, f32 radius_sqr, u16 cur_sector) {\n"
    if s.count(sig)!=1: raise ValueError("radius collision signature changed")
    s=s.replace(sig,sig+"    fix32 manifold_ox = curx, manifold_oy = cury; u16 manifold_os = cur_sector;\n",1)
    start=s.index(sig)
    k=s.index("    collision_result res;\n",start)
    s=s[:k]+"""    if (!within_sector(curx, cury, cur_sector)) {
        s16 f = manifold_locate2(curx, cury, cur_sector);
        if (f >= 0) { cur_sector = f; }
        else { curx = manifold_ox; cury = manifold_oy; cur_sector = manifold_os; }
    }
"""+s[k:]
    p.write_text(s)
    print("collision: corner crossings resolved or blocked")

def far_portal_fog(out):
    """E1M1 views reach 40-90 cell visits per frame (2-7 fps) and recursion
    depth 18+, where the stack guard starts dropping portals (flicker).
    Portals entirely beyond MANIFOLD_FAR map units are drawn as solid walls
    instead of being entered: bounded cost and depth, stable image."""
    far=int(os.environ.get("MANIFOLD_FAR","1600"))
    p=out/"src/portal.c"
    s=p.read_text()
    old="""        Vect2D_s16 trans_v1 = *transformed_vert_buffer_ptr++;
        Vect2D_s16 trans_v2 = *transformed_vert_buffer_ptr++;
"""
    if s.count(old)<1: raise ValueError("visit_graph transform layout changed")
    new=old+f"""        u8 manifold_fogged = 0;
        if (is_portal && trans_v1.y > ({far}<<TRANS_Z_FRAC_BITS) && trans_v2.y > ({far}<<TRANS_Z_FRAC_BITS)) {{
            is_portal = 0; portal_sector = -1; manifold_fogged = 1;
        }}
"""
    s=s.replace(old,new,1)
    o2="        u8 is_solid_color = map->wall_colors[(portal_idx<<WALL_COLOR_NUM_PARAMS_SHIFT)+WALL_SOLID_COLOR_IDX];\n"
    if s.count(o2)<1: raise ValueError("solid colour read changed")
    s=s.replace(o2,o2+"        if (manifold_fogged) { is_solid_color = 1; }  /* darkest palette entry = distance fog */\n",1)
    p.write_text(s)
    print("far portals fogged at",far)

def clamp_native_vertical_lines(out):
    """Flat-colour column filler jumps into an unrolled table sized for
    dy<=158 and writes from col_ptr+y0*2 with no bounds checks. E1M1 feeds
    it y0<0 / y1>SCREEN_HEIGHT / y1<y0, which wrote below the framebuffer
    into the heap (objects[]), later crashing via a garbage object state
    pointer (LINE 1111 / 'execute at unmapped address' in BlastEm)."""
    p=out/"src/draw.c"
    s=p.read_text()
    old="void draw_native_vertical_line_unrolled(s16 y0, s16 y1, u32 full_col,  u8* col_ptr) {\n"
    if s.count(old)!=1: raise ValueError("draw_native_vertical_line_unrolled signature changed")
    s=s.replace(old,old+"    if (y0 < 0) { y0 = 0; }\n    if (y1 > SCREEN_HEIGHT) { y1 = SCREEN_HEIGHT; }\n    if (y1 <= y0) { return; }\n",1)
    p.write_text(s)
    print("flat column filler clamped to 0..SCREEN_HEIGHT")

def apply_doom_textures(out, lumps, cells, wad):
    """M04: real Doom wall textures, flats colours and a dedicated palette."""
    import re
    import wad_textures as WT
    from emit_portal_map import assign_wall_textures, _nm
    names=assign_wall_textures(lumps,cells)
    default="STARTAN3" if "STARTAN3" in names else names[0]
    if len(names)>64: raise ValueError(f"{len(names)} textures > Manifold limit 64")
    flats=sorted({_nm(x) for sec in lumps["SECTORS"] for x in (sec[2],sec[3])})
    res=WT.build_resources(wad,names,[f for f in flats if f!="F_SKY1"])
    pal=res["pal"]
    tex={"index":{n:i for i,n in enumerate(names)},"default":default,
         "avg":{n:WT.nearest(pal,WT.average(res["tex"][n][2])) for n in names},
         "width":{n:res["tex"][n][0] for n in names},
         "flat_color":{f:WT.nearest(pal,WT.average(img)) for f,img in res["flats"].items()},
         "vdp_palette":[WT.vdp(c) for c in pal]}
    tex["flat_color"]["F_SKY1"]=0          # transparent: sky shows behind
    tex["floor_color"]={i:tex["flat_color"].get(_nm(sec[2]),13) for i,sec in enumerate(lumps["SECTORS"])}
    # textures.c: replace upstream atlas + table, keep the rest of the file
    t=out/"src/textures.c"
    src=t.read_text()
    a=src.index("const u16 raw_texture_atlas")
    b=src.index("const lit_texture* const textures[")
    b=src.index("};",b)+2
    gen=WT.emit_textures_c(res,names)
    gen=gen.split('/* GENERATED',1)[1]
    src=src[:a]+"/* GENERATED"+gen+src[b:]
    t.write_text(src)
    # colors.c light tables recomputed for the new palette
    c=out/"src/colors.c"
    cs=c.read_text()
    dith,nodith=WT.colors_tables(pal)
    for name_,body in (("dither_color_calc_table",dith),("no_dither_color_calc_table",nodith)):
        m=re.search(r"(const u32 "+name_+r"\[16\*5\*2\] = \{)(.*?)(\n\};)",cs,re.S)
        if not m: raise ValueError(f"{name_} not found in colors.c")
        cs=cs[:m.start(2)]+"\n"+body+cs[m.end(2):]
    c.write_text(cs)
    if res.get("sky") and os.environ.get("MANIFOLD_SKY","1")=="1": install_sky(out,res)
    print("doom textures:",len(names),"flats:",len(flats),"palette:",[hex(v) for v in tex["vdp_palette"]])
    return tex

def textured_portal_steps(out):
    """Upper/lower portal walls (steps, door frames, window sills) were only
    textured for DOOR/LIFT groups. The emitter now encodes a texture index
    as 0x80|idx in the high/low colour bytes; use the textured step drawers
    whenever that flag is set (top-pegged upper, bottom-pegged lower)."""
    p=out/"src/portal.c"
    s=p.read_text()
    old_u="""                if(neighbor_sector_group_type == DOOR && !is_solid_color) {
                    //continue;
                    draw_top_pegged_textured_upper_step("""
    new_u="""                if((neighbor_sector_group_type == DOOR && !is_solid_color) || (upper_color & 0x80)) {
                    if (upper_color & 0x80) {
                        tmap_info.tex = get_texture(upper_color & 0x7F, light_level);
                        if (neighbor_sector_group_type != DOOR) { x1_pegged = x1_ytop; x2_pegged = x2_ytop; }
                    }
                    draw_top_pegged_textured_upper_step("""
    old_l="""                if(neighbor_sector_group_type == LIFT && !is_solid_color) {
                    draw_bottom_pegged_textured_lower_step("""
    new_l="""                if((neighbor_sector_group_type == LIFT && !is_solid_color) || (lower_color & 0x80)) {
                    if (lower_color & 0x80) {
                        tmap_info.tex = get_texture(lower_color & 0x7F, light_level);
                        if (neighbor_sector_group_type != LIFT) { x1_pegged = x1_ybot; x2_pegged = x2_ybot; }
                    }
                    draw_bottom_pegged_textured_lower_step("""
    for o,n_ in ((old_u,new_u),(old_l,new_l)):
        if s.count(o)!=1: raise ValueError("portal step layout changed")
        s=s.replace(o,n_,1)
    p.write_text(s)
    print("portal upper/lower steps textured")

def keep_overlays_off_sky(out):
    """The console line (BG_B row 4) and the fps counter (BG_B row 5) were
    drawn over the sky band rows. Move them into the black top border."""
    c=out/"src/console.c"; cs=c.read_text()
    if "#define CONSOLE_BASE_Y 4\n" not in cs: raise ValueError("console row changed")
    c.write_text(cs.replace("#define CONSOLE_BASE_Y 4\n","#define CONSOLE_BASE_Y 1\n",1))
    g=out/"src/game.c"; gs=g.read_text()
    old="void showStats() {\n    char str[32];\n    u16 y = 5;\n"
    if old not in gs: raise ValueError("showStats layout changed")
    gs=gs.replace(old,"void showStats() {\n    char str[32];\n    u16 y = 5;\n",1)
    # rows outside the 3D view are blanked by the bitmap's extended blank:
    # keep the counter in the left border columns 0-3 of a viewport row
    o="    u16 base = TILE_FONT_INDEX;\n    u8 x = 2;\n"
    if o not in gs: raise ValueError("showStats x layout changed")
    gs=gs.replace(o,"    u16 base = TILE_FONT_INDEX;\n    u8 x = 0;\n",1)
    g.write_text(gs)
    print("console/fps moved to top border")

def scale_light_distances(out):
    """Upstream lighting bands (mid 150 / dark 350 / fade 400 units) suit its
    small test maps. In E1M1 walls beyond 400 units hit the FADE band, which
    writes colour 0 = transparent (BG_B shows through: 'texture lost far
    away'). Scale the bands to E1M1 and push FADE beyond the fog distance."""
    p=out/"src/colors.h"
    s=p.read_text()
    for a,b in (("#define MID_DIST 150","#define MID_DIST 320"),("#define MID_DARK_DIST 250","#define MID_DARK_DIST 520"),
                ("#define DARK_DIST 350","#define DARK_DIST 760"),("#define FADE_DIST 400","#define FADE_DIST 4000")):
        if a not in s: raise ValueError(f"colors.h changed: {a}")
        s=s.replace(a,b,1)
    p.write_text(s)
    print("light distance bands scaled for E1M1")

def weapon_buffers_fit_vram(out):
    """SGDK 2 rescomp gives shotgun_reload 128 tiles/frame (MAX_SPRITE_TILES
    was 97 -> assert 'Weapon has too many sprite tiles' when pressing A).
    Use 128-tile buffers: buffer 0 in the normal tile area, buffer 1 in the
    reclaimed WINDOW nametable (exactly 128 tiles; window is never shown)."""
    p=out/"src/weapon_sprites.c"
    s=p.read_text()
    reps=[("#define MAX_SPRITE_TILES 97\n","#define MAX_SPRITE_TILES 128\n"),
          ("        return start_tile_loc + MAX_SPRITE_TILES;\n","        return manifold_weapon_buf1;\n"),
          ("    start_tile_loc = tile_loc;\n","    start_tile_loc = tile_loc;\n    VDP_setWindowAddress(bgb_addr);   /* window unused: reuse its 4KB */\n    manifold_weapon_buf1 = window_addr_tiles_before_move;\n"),
          ("    return tile_loc+(MAX_SPRITE_TILES*2);\n","    return tile_loc+MAX_SPRITE_TILES;\n")]
    for a,b in reps:
        if s.count(a)!=1: raise ValueError(f"weapon_sprites layout changed: {a!r}")
        s=s.replace(a,b,1)
    s=s.replace("u32 init_weapon_sprites(u32 tile_loc) {\n","static u16 manifold_weapon_buf1;\nu32 init_weapon_sprites(u32 tile_loc) {\n    u16 window_addr_tiles_before_move = window_addr >> 5;\n",1)
    p.write_text(s)
    print("weapon: 2x128-tile buffers (second in reclaimed window VRAM)")

def fix_fps_font_base(out):
    """Upstream fps counter hard-codes the SGDK 1.x font tile base 0x5A0;
    SGDK 2 puts the font at TILE_FONT_INDEX (0x4E0 here). 0x5A0 is the
    WINDOW nametable area that we now reclaim for tiles."""
    p=out/"src/game.c"
    s=p.read_text()
    old="    u16 base = 0x05A0;\n"
    if s.count(old)!=1: raise ValueError("fps font base changed")
    p.write_text(s.replace(old,"    u16 base = TILE_FONT_INDEX;\n",1))
    print("fps font base -> TILE_FONT_INDEX")

def install_sky(out, res):
    """SKY1 band on BG_B behind the framebuffer (BG_A colour 0 = sky
    ceilings), 256px wide like Doom (90 degrees), tiles stored in VRAM
    reclaimed from the unused WINDOW nametable and the never-displayed
    rows 28-63 of the 64x64 BG_B nametable (~272 tiles)."""
    import wad_textures as WT
    sk=WT.sky_tiles(res, band_rows=10, band_cols=16, max_tiles=134)
    n=len(sk["tiles"]);rows=sk["rows"];cols=sk["cols"]
    tiles=",\n".join("  "+",".join(f"0x{v:08x}" for v in t) for t in sk["tiles"])
    tmap=",".join(str(v) for row in sk["map"] for v in row)
    band_top=4   # Doom: sky texture top at the top of the view, mountains reach the horizon
    c=f"""#include "manifold_mute_klog.h"
#include <genesis.h>
#include "game.h"
/* GENERATED: Doom SKY1 band, 3D palette (PAL1) */
static const u32 sky_tiles[{n}*8] = {{
{tiles}
}};
static const u8 sky_map[{rows}][{cols}] = {{ {tmap} }};
static u16 sky_index[{n}];
static s16 sky_last = -1;
static u8 sky_ready = 0;
static u16 sky_row_buf[{rows}*32];
u16 manifold_reclaimed_tiles = 0;
/* VRAM reclaim: WINDOW map is unused (window disabled) -> point it at
   BG_B and use its 4KB for tiles; BG_B rows 28..63 are never displayed
   (no BG_B scroll) -> 4.5KB more. */
u16 manifold_sky_init(u16 free_tile_loc) {{
    /* WINDOW area is taken by the weapon's second buffer */
    u16 r2 = (bgb_addr + 30 * 128) >> 5;           /* rows 30-63: HUD reaches row 28 */
    u16 r2n = ((bgb_addr + 0x2000) >> 5) - r2;
    manifold_reclaimed_tiles = 128 + r2n;
    if ({n} > r2n) return free_tile_loc;
    for (u16 k = 0; k < {n}; k++) {{
        sky_index[k] = r2 + k;
        VDP_loadTileData(&sky_tiles[k*8], sky_index[k], 1, CPU);
    }}
    for (u16 r = 0; r < 18; r++) {{
        u16 t = TILE_ATTR_FULL(PAL1, 0, 0, 0, sky_index[1]);
        if (r >= {band_top - 4} && r < {band_top - 4 + rows}) continue;
        for (u16 c = 0; c < 32; c++) sky_row_buf[c] = t;
        VDP_setTileMapDataRect(BG_B, sky_row_buf, 4, 4 + r, 32, 1, 32, CPU);
    }}
    sky_ready = 1; sky_last = -1;
    return free_tile_loc;
}}
void manifold_sky_update(void) {{
    if (!sky_ready) return;
    s16 off = (s16)((cur_player_pos.ang >> 4) & {cols - 1});
    if (off == sky_last) return;
    sky_last = off;
    for (u16 r = 0; r < {rows}; r++)
        for (u16 c = 0; c < 32; c++)
            sky_row_buf[r*32 + c] = TILE_ATTR_FULL(PAL1, 0, 0, 0, sky_index[sky_map[r][(c + off) & {cols - 1}]]);
    VDP_setTileMapDataRect(BG_B, sky_row_buf, 4, {band_top}, 32, {rows}, 32, CPU);
}}
"""
    (out/"src/manifold_sky.c").write_text(c)
    g=out/"src/game.c"
    gs=g.read_text()
    old="    free_tile_loc = console_init(free_tile_loc);\n"
    if gs.count(old)!=1: raise ValueError("console_init call changed")
    gs=gs.replace(old,old+"    free_tile_loc = manifold_sky_init(free_tile_loc);\n",1)
    gs=gs.replace("u16 free_tile_loc;\n","u16 free_tile_loc;\nu16 manifold_sky_init(u16 free_tile_loc);\n",1)
    g.write_text(gs)
    j=out/"src/joy_helper.c"
    js=j.read_text()
    old="void update_joy() {\n"
    if js.count(old)!=1: raise ValueError("update_joy changed")
    js=js.replace(old,"void manifold_sky_update(void);\n"+old+"    manifold_sky_update();\n",1)
    j.write_text(js)
    print("sky tiles:",n,"band rows:",rows,"cols:",cols)

def tour_input(out, cells, lumps):
    """Test-only camera tour: every 90 frames teleport to the centroid of the
    largest cell of each Doom sector and spin (LEFT held). Exercises the whole
    map's geometry/renderer for screenshots, fps and recursion-guard counts."""
    best={}
    for c in cells:
        pts=[(w["a"][0]/16,w["a"][1]/16) for w in c["walls"]]
        a2=sum(pts[k][0]*pts[(k+1)%len(pts)][1]-pts[(k+1)%len(pts)][0]*pts[k][1] for k in range(len(pts)))
        if a2==0: continue
        cx=sum((pts[k][0]+pts[(k+1)%len(pts)][0])*(pts[k][0]*pts[(k+1)%len(pts)][1]-pts[(k+1)%len(pts)][0]*pts[k][1]) for k in range(len(pts)))/(3*a2)
        cy=sum((pts[k][1]+pts[(k+1)%len(pts)][1])*(pts[k][0]*pts[(k+1)%len(pts)][1]-pts[(k+1)%len(pts)][0]*pts[k][1]) for k in range(len(pts)))/(3*a2)
        s_=c["doom_sector"]
        if s_ not in best or abs(a2)>best[s_][0]: best[s_]=(abs(a2),round(cx),round(cy),c["id"])
    keys=sorted(best)
    if os.environ.get("MANIFOLD_TOUR_SKY")=="1":
        keys=[k for k in keys if lumps["SECTORS"][k][3].rstrip(b"\0")==b"F_SKY1"] or keys
    pts=[best[k] for k in keys]
    j=out/"src/joy_helper.c"
    code=j.read_text()
    arr=",".join(f"{{{x},{y},{cid}}}" for _,x,y,cid in pts)
    code+=f"""
#include "game.h"
#include "sector_group.h"
#include "portal_map.h"
#include "level.h"
static const s16 manifold_tour[][3] = {{{arr}}};
volatile u16 manifold_tour_idx = 0xFFFF;
u16 manifold_autopilot_joy(u16 j) {{
    (void)(JOY_readJoypad)(j);
    u32 f = vtimer;
    if (f < 60) return 0;
    u16 idx = ((f - 60) / 90) % {len(pts)};
    if (idx != manifold_tour_idx) {{
        manifold_tour_idx = idx;
        cur_player_pos.x = FIX32(manifold_tour[idx][0]);
        cur_player_pos.y = FIX32(manifold_tour[idx][1]);
        cur_player_pos.cur_sector = manifold_tour[idx][2];
        u16 g = sector_group(manifold_tour[idx][2], (portal_map*)cur_portal_map);
        cur_player_pos.z = (get_sector_group_floor_height(g)<<(FIX32_FRAC_BITS-4)) + FIX32(82);
    }}
    return BUTTON_LEFT;
}}
"""
    j.write_text(code)
    print("tour points:",len(pts))

def autopilot_input(out):
    """Test-only: replace JOY_readJoypad with a scripted walk so headless
    BlastEm (no pad input) exercises movement/turning. Enabled via
    MANIFOLD_EXTRA=autopilot_input for the 'autowalk' ROM only."""
    base=out/"src"
    h=base/"manifold_mute_klog.h"
    h.write_text(h.read_text()+"""
u16 manifold_autopilot_joy(u16 j);
#define JOY_readJoypad(j) manifold_autopilot_joy(j)
""")
    j=base/"joy_helper.c"
    j.write_text(j.read_text()+"""
u16 manifold_autopilot_joy(u16 j) {
    (void)(JOY_readJoypad)(j);
    u32 f = vtimer;
    if (f < 120) { return 0; }   /* map autoloads; START would pause */
    u32 t = (f - 120) % 1400;
    if (t < 240) return BUTTON_UP;
    if (t < 290) return BUTTON_RIGHT;
    if (t < 500) return BUTTON_UP;
    if (t < 600) return BUTTON_LEFT;
    if (t < 840) return BUTTON_UP | BUTTON_LEFT;
    if (t < 960) return BUTTON_DOWN;
    if (t < 1100) return BUTTON_RIGHT;
    if (t < 1300) return BUTTON_UP | BUTTON_RIGHT;
    return BUTTON_LEFT;
}
""")
    print("autopilot joypad script installed (test ROM only)")

def keep_display_enabled_in_hblank(out):
    """Diagnostic/optional: never blank the display from the H-Int phase
    machine (VBlank DMA then spills into active display instead)."""
    p=out/"src/my_bmp.c"
    s=p.read_text()
    a=s.index("HINTERRUPT_CALLBACK bmp_do_hblank_process_vertical() {")
    b=s.index("HINTERRUPT_CALLBACK bmp_do_hblank_process_horizontal() {")
    body=s[a:b]
    if body.count("VDP_setEnable(0);")!=1:
        raise ValueError("vertical H-Int body changed")
    s=s[:a]+body.replace("VDP_setEnable(0);","/* display kept on */")+s[b:]
    p.write_text(s)
    print("H-Int no longer disables the display")

def restore_generated_scalers_with_correct_constraints(out):
    """Use upstream's generated 68000 jump-table texture scalers again.

    The upstream wrappers wrote input-only operands (`f`, unclipped_dy*4)
    and JSR'd into code that rewrites d0/d1/a0/a1 without telling GCC.
    Here the table entry is fetched in C and the call declares every
    register the generated routine touches. The ADDRESS ERROR originally
    blamed on these tables came from the SGDK2 H-Int callback (fixed).
    """
    p=out/"src/texture.c"
    source=p.read_text()
    replacements={
        "draw_texture_vertical_line": """
static void manifold_wall_column_c(s16 uy0, s16 y0, s16 uy1, s16 y1,
                                   u8* col_ptr, const u16* tex_column) {
    s16 dy = uy1 - uy0;
    if (dy <= 0 || y1 <= y0) { return; }
    u32 step = (((u32)64) << 16) / (u32)dy;
    u32 pos = (u32)(y0 - uy0) * step;
    u16* dst = (u16*)(col_ptr + ((u16)y0 << 1));
    s16 n = y1 - y0;
    while (n-- > 0) {
        *dst++ = tex_column[pos >> 16];
        pos += step;
    }
}

void draw_texture_vertical_line(s16 unclipped_y0, u16 y0, s16 unclipped_y1,
                                u8* col_ptr, const u16* tex_column) {
    s16 sy0 = (s16)y0;
    if (sy0 < unclipped_y0) { sy0 = unclipped_y0; }
    if (sy0 < 0) { sy0 = 0; }
    if (unclipped_y1 > SCREEN_HEIGHT) { draw_bottom_clipped_texture_vertical_line(unclipped_y0, (u16)sy0, unclipped_y1, SCREEN_HEIGHT, col_ptr, tex_column); return; }
    if (sy0 >= unclipped_y1) { return; }
    s16 dy = unclipped_y1 - unclipped_y0;
    if (dy <= 0) { return; }
    if (dy > 512) {
        manifold_wall_column_c(unclipped_y0, sy0, unclipped_y1, unclipped_y1, col_ptr, tex_column);
        return;
    }
    u16 unclipped_dy = (u16)dy;
    u16 clip_top = (u16)(sy0 - unclipped_y0);
    void* f = (void*)jump_table_top_clip_lut[unclipped_dy];
    register u32 d0 asm ("%d0") = clip_top;
    register const u16* a0 asm ("%a0") = tex_column;
    register u8* a1 asm ("%a1") = col_ptr + ((u16)sy0 << 1);
    __asm volatile("jsr (%3)"
        : "+d" (d0), "+a" (a0), "+a" (a1)
        : "a" (f)
        : "d1", "cc", "memory");
}
""",
        "draw_bottom_clipped_texture_vertical_line": """
void draw_bottom_clipped_texture_vertical_line(s16 unclipped_y0, u16 y0,
                                                s16 unclipped_y1, u16 y1,
                                                u8* col_ptr, const u16* tex_column) {
    s16 sy0 = (s16)y0;
    s16 sy1 = (s16)y1;
    if (sy0 < unclipped_y0) { sy0 = unclipped_y0; }
    if (sy1 > unclipped_y1) { sy1 = unclipped_y1; }
    if (sy0 < 0) { sy0 = 0; }
    if (sy1 > SCREEN_HEIGHT) { sy1 = SCREEN_HEIGHT; }
    if (sy1 <= sy0) { return; }
    s16 dy = unclipped_y1 - unclipped_y0;
    if (dy <= 0) { return; }
    if (dy > 512) {
        manifold_wall_column_c(unclipped_y0, sy0, unclipped_y1, sy1, col_ptr, tex_column);
        return;
    }
    u16 unclipped_dy = (u16)dy;
    u16 clip_top = (u16)(sy0 - unclipped_y0);
    u16 clip_bot = (u16)(unclipped_y1 - sy1);
    void* f = (void*)jump_table_bot_clip_lut[unclipped_dy];
    register u32 d0 asm ("%d0") = clip_top;
    register u32 d1 asm ("%d1") = clip_bot;
    register const u16* a0 asm ("%a0") = tex_column;
    register u8* a1 asm ("%a1") = col_ptr + ((u16)sy0 << 1);
    __asm volatile("jsr (%4)"
        : "+d" (d0), "+d" (d1), "+a" (a0), "+a" (a1)
        : "a" (f)
        : "cc", "memory");
}
"""
    }
    import re
    for name,replacement in replacements.items():
        matches=list(re.finditer(r"\bvoid\s+"+name+r"\s*\(",source))
        if len(matches)!=1:
            raise ValueError(f"expected one scaler wrapper {name}, got {len(matches)}")
        start=matches[0].start()
        opening=source.index("{",matches[0].end())
        depth=1;end=opening+1
        while depth and end<len(source):
            if source[end]=="{": depth+=1
            elif source[end]=="}": depth-=1
            end+=1
        source=source[:start]+replacement+source[end:]
    if "tex_tables_lookup.h" not in source:
        source='#include "tex_tables_lookup.h"\n'+source
    source='#include "utils.h"\nvoid draw_bottom_clipped_texture_vertical_line(s16, u16, s16, u16, u8*, const u16*);\n'+source
    p.write_text(source)
    print("Generated jump-table scalers restored with explicit register contracts")

def instrument_portal_renderer(out):
    """Cumulative counters readable from an emulator (no behavior change):
    manifold_dbg[0]=visit_graph calls, [1]=walls seen, [2]=unclipped,
    [3]=near-z culled, [4]=frustum culled, [5]=other clip results,
    [6]=portal_rend calls."""
    p=out/"src/portal.c"
    s=p.read_text()
    old="void visit_graph(u16 src_sector, u16 sector, u16 x1, u16 x2, u32 cur_frame, uint8_t depth) {"
    if s.count(old)!=1: raise ValueError("visit_graph signature changed")
    s=s.replace(old,"volatile u32 manifold_dbg[8];\n"+old+"\n    manifold_dbg[0]++;",1)
    old="        clip_result clipped = clip_map_vertex_16((Vect2D_s16*)&trans_v1, (Vect2D_s16*)&trans_v2, &tmap_info);\n"
    if s.count(old)<1: raise ValueError("clip call changed")
    s=s.replace(old,old+"        manifold_dbg[1]++; manifold_dbg[clipped==UNCLIPPED?2:clipped==NEAR_Z_CULLED?3:clipped==FRUSTUM_CULLED?4:5]++;\n",1)
    old="void portal_rend(u16 src_sector, u32 cur_frame) {"
    if s.count(old)!=1: raise ValueError("portal_rend changed")
    s=s.replace(old,old+"\n    manifold_dbg[6]++;",1)
    p.write_text(s)
    print("portal renderer instrumented (manifold_dbg)")

def default_texture_repetitions(out):
    """Upstream test maps leave wall_tex_repetitions NULL; the renderer then
    read ROM vector bytes as repetition counts (0 under SGDK2 boot -> every
    column sampled texture column 0). Default to 1 when absent."""
    p=out/"src/portal.c"
    s=p.read_text()
    old="map->wall_tex_repetitions[portal_idx]"
    n=s.count(old)
    if n<1: raise ValueError("repetition lookup changed")
    s=s.replace(old,"(map->wall_tex_repetitions ? map->wall_tex_repetitions[portal_idx] : 1)")
    p.write_text(s)
    print("texture repetitions default to 1 when map has none:",n)

def poll_joypad_each_frame(out):
    """SGDK 1.x refreshed joypad state inside its V-Int handler; SGDK 2.x
    only does it in SYS_doVBlankProcess(), which Manifold never calls (it
    owns V-Int via do_vint_flip). Without this the pad reads as idle."""
    p=out/"src/joy_helper.c"
    s=p.read_text()
    old="void update_joy() {\n"
    if s.count(old)!=1: raise ValueError("update_joy changed")
    s=s.replace(old,old+"    JOY_update();\n")
    p.write_text(s)
    print("JOY_update() polled once per game frame")

def saturate_far_depth_and_guard_windows(out):
    """Upstream test maps fit in +-2047 units; E1M1 spans ~4000, so the
    12.4 view depth `ry >> 2` wrapped in s16 and far vertices reappeared as
    near ghosts with absurd projections (seen as an odd column pointer /
    ADDRESS ERROR while turning). Saturate depth and lateral values, and
    reject degenerate portal windows on entry to visit_graph."""
    p=out/"src/math3d.c"
    s=p.read_text()
    reps={
        "    s16 cur_res_x = rx>>(FIX16_FRAC_BITS);\n":
        "    s16 cur_res_x = MANIFOLD_SAT16(rx>>(FIX16_FRAC_BITS));\n",
        "    s16 cur_res_y = ry>>(FIX16_FRAC_BITS-TRANS_Z_FRAC_BITS); // 12.4\n":
        "    s16 cur_res_y = MANIFOLD_SAT16(ry>>(FIX16_FRAC_BITS-TRANS_Z_FRAC_BITS)); // 12.4\n",
        "        cur_res_x = rx >> (FIX16_FRAC_BITS);                   \n":
        "        cur_res_x = MANIFOLD_SAT16(rx >> (FIX16_FRAC_BITS));\n",
        "        cur_res_y = ry >> (FIX16_FRAC_BITS-TRANS_Z_FRAC_BITS);     \n":
        "        cur_res_y = MANIFOLD_SAT16(ry >> (FIX16_FRAC_BITS-TRANS_Z_FRAC_BITS));\n",
    }
    for old,new in reps.items():
        if s.count(old)!=1:
            raise ValueError(f"math3d transform line changed: {old!r}")
        s=s.replace(old,new)
    s=("#define MANIFOLD_SAT16(v) ((s16)(((s32)(v)) > 32767 ? 32767 : (((s32)(v)) < -32768 ? -32768 : (s32)(v))))\n"+s)
    p.write_text(s)
    p=out/"src/portal.c"
    s=p.read_text()
    old="    manifold_dbg[0]++;"
    if s.count(old)!=1: raise ValueError("instrumentation anchor missing")
    s=s.replace(old,old+"\n    if (x2 > RENDER_WIDTH) x2 = RENDER_WIDTH;\n    if (x1 >= x2) return;",1)
    p.write_text(s)
    print("far depth saturated; visit_graph windows validated")

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
    for step in (stage_missing_resources,normalize_legacy_asm,namespace_legacy_allocators,normalize_legacy_s16_bounds,normalize_legacy_fixed_point_api,normalize_wide_sprite_registers,normalize_legacy_palette_and_asm,normalize_game_integration,normalize_weapon_api_declaration,normalize_remaining_palettes,normalize_menu_callbacks,normalize_math_and_menu,normalize_bitmap_legacy_symbols,normalize_pvs_entry_types,normalize_toggle_declarations,normalize_weapon_sprite_frame_layout,normalize_header_global_definitions,mute_legacy_emulator_debug_logging,restore_generated_scalers_with_correct_constraints,fix_sgdk2_hint_callbacks,harden_inline_asm,fail_loud_on_heap_exhaustion,widen_sector_vertex_buffers,relocate_free_tiles_after_sgdk2_framebuffer,instrument_portal_renderer,default_texture_repetitions,poll_joypad_each_frame,saturate_far_depth_and_guard_windows,clamp_native_vertical_lines,guard_portal_recursion_stack,robust_sector_crossing,far_portal_fog,fix_fps_font_base,textured_portal_steps,keep_overlays_off_sky,scale_light_distances,weapon_buffers_fit_vram,):
        if step.__name__ in skip:
            print('SKIPPED stage step:',step.__name__); continue
        step(out)
    for extra in filter(None,os.environ.get('MANIFOLD_EXTRA','').split(',')):
        print('EXTRA stage step:',extra); globals()[extra](out)
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
    tex=None
    if os.environ.get("MANIFOLD_CELLS","exact")=="exact" and os.environ.get("MANIFOLD_TEXTURES","1")=="1":
        tex=apply_doom_textures(out,map_lumps,cells,wad)
    (out/"src/e1m1_map.c").write_text(emit(map_lumps,cells,tex))
    if "tour_input" in os.environ.get("MANIFOLD_TOUR",""):
        h=out/"src/manifold_mute_klog.h"
        h.write_text(h.read_text()+"\nu16 manifold_autopilot_joy(u16 j);\n#define JOY_readJoypad(j) manifold_autopilot_joy(j)\n")
        tour_input(out,cells,map_lumps)
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
    sc=[c for c in cells if c["id"]==spawn_cell][0]
    print("SPAWN CELL", spawn_cell, "index", cells.index(sc), "doom_sector", sc["doom_sector"])
    for w in sc["walls"]:
        print("  wall", [v/16 for v in w["a"]], "->", [v/16 for v in w["b"]], "neighbor", w["neighbor"], "seg", w["seg"])
    ids=[c["id"] for c in cells]
    print("cell ids contiguous:", ids==list(range(len(ids))), "first ids", ids[:8])
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
    # Doom eye height 41 units x HEIGHT_SCALE 2; Manifold keeps the camera on the floor.
    eye="(FIX32_FRAC_BITS-4));// + FIX32(50);"
    if s.count(eye)!=1:
        raise ValueError("level.c player z init changed")
    s=s.replace(eye,"(FIX32_FRAC_BITS-4)) + FIX32(82);")
    g=out/"src/game.c"
    gs=g.read_text()
    if gs.count(eye)!=1:
        raise ValueError("game.c rest z changed")
    gs=gs.replace(eye,"(FIX32_FRAC_BITS-4)) + FIX32(82);")
    feet="        s16 cur_player_z = cur_player_pos.z >> (FIX32_FRAC_BITS-4);"
    if gs.count(feet)!=1:
        raise ValueError("game.c collision z changed")
    gs=gs.replace(feet,"        s16 cur_player_z = (cur_player_pos.z - FIX32(82)) >> (FIX32_FRAC_BITS-4); /* feet, not eye */")
    g.write_text(gs)
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
