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

MAX_WALLS_PER_SECTOR=int(os.environ.get("MANIFOLD_MAX_CELL_WALLS","16"))  # E1M1 BSP cells have <=11 walls; 255 made visit_graph frames 2.3KB -> stack overflow into heap
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
        if (depth > 48 || (sp_now & 0xFFFFFF) < ((manifold_heap_high & 0xFFFFFF) + @STK@)) { manifold_dbg[7]++; return; }
        if (depth > manifold_dbg_maxdepth) { manifold_dbg_maxdepth = depth; }
    }""",1)
    s=s.replace("@STK@",os.environ.get("MANIFOLD_STACK_MARGIN","3072"))
    p.write_text(s)
    print("portal recursion bounded by stack/heap guard, margin",os.environ.get("MANIFOLD_STACK_MARGIN","3072"))

def guard_zero_width_edges(out):
    """M12: 68000 DIVS-by-zero when a wall/floor/ceiling edge has x1 == x2.

    H40 autowalk, BlastEm 1.0.0 (runner run 43020524524): vector 5 (zero divide)
    at ~frame 1012. Stacked PC 0xA233E = divuw inside __udivsi3; caller
    __divsi3 at 0x5DD0 = draw_floor_update_clip(+0x14), reached from portal.c.
    Every edge slope is (dy<<12)/dx with dx = x2-x1, unguarded in draw.c.
    Only dx == 0 is changed (no visible width); dx < 0 keeps old behaviour.
    """
    p=out/"src/draw.c"
    s=p.read_text()
    guard="    if (dx == 0) return; /* M12: zero-width edge would trap on DIVS */\n"
    if guard in s:
        return
    old="    s16 dx = x2-x1;\n"
    n=s.count(old)
    if n!=9:
        raise ValueError(f"unexpected dx=x2-x1 site count: {n}")
    s=s.replace(old,old+guard)
    p.write_text(s)
    print("zero-width edges guarded in draw.c (9 sites)")

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

def guard_zero_reciprocal_in_texture_columns(out):
    """Prevent 68000 DIVU-by-zero in far-away outdoor texture perspective.

    M06 BlastEm ZERO DIVIDE: PC offset 0x3530, preceding instruction
    0x352e = divu.w %d4,%d2, in calculate_tex_coords_for_wall.
    %d4 is one_over_z_16_span_end, rounded to zero at far depth.
    Prefer the previous reciprocal rather than discontinuous near/infinite U.
    """
    p=out/"src/draw.c"
    s=p.read_text()
    start="    u16 one_over_z_16 = one_over_z_26>>10;\n"
    n=s.count(start)
    if n<2:
        raise ValueError(f"unexpected starting reciprocal count: {n}")
    s=s.replace(start,start+"    if (one_over_z_16 == 0) one_over_z_16 = 1; /* far-depth Q16 underflow */\n")
    for old in (
        "        one_over_z_16_span_end = one_over_z_16 + d_one_over_z_16_times_4;\n",
        "        u16 one_over_z_16_span_end = one_over_z_16 + d_one_over_z_16_times_2;\n",
    ):
        if s.count(old)!=1:
            raise ValueError(f"unexpected ending reciprocal expression {old!r}")
        s=s.replace(old,old+"        if (one_over_z_16_span_end == 0) one_over_z_16_span_end = one_over_z_16;\n",1)
    p.write_text(s)
    print("Guarded zero reciprocal for far outdoor texture columns")


def limit_repeated_sector_overdraw(out):
    """Bound repeated BSP cell rendering in dense stair corridors.

    Manifold visits a sector seven times per frame by default
    (sector_rendered_cache >= 14); cap at five visits (>=10).
    This is an experimental visual/FPS tradeoff, not a culling proof.
    """
    p=out/"src/portal.c"
    source=p.read_text()
    old="if(sector_rendered_cache[sector] >= 14)"
    if source.count(old)!=1:
        raise ValueError("upstream repeated-sector threshold changed")
    visits=int(os.environ.get("MANIFOLD_VISITS","5"))
    source=source.replace(old,"if(sector_rendered_cache[sector] >= %d)"%(2*visits))
    p.write_text(source)
    print("Portals: per-frame repeated-sector bound %d (upstream 7)"%visits)



def cache_transformed_vertices(out):
    """M11 A/B: cache the 12.4 transformed vertex once per 3D frame.

    Upstream transforms every vertex again for every cell/portal revisit.
    Cache all (x,z) transformed coordinates by map vertex ID. No geometric
    clipping or portal traversal is cached: every call still receives a fresh
    per-wall buffer and can clip it independently. 6 bytes per map vertex.
    """
    p=out/"src/portal.c"
    source=p.read_text()
    decl="u8* sector_rendered_cache; // i don't know if this helps much, but we might be able to use it\n"
    if source.count(decl)!=1:
        raise ValueError("portal vertex cache allocation anchor changed")
    code=r"""
static Vect2D_s16 *m11_vertex_xy;
static u16 *m11_vertex_stamp;
static u16 m11_vertex_epoch = 1;
volatile u32 m11_vertex_cache_hits;
volatile u32 m11_vertex_cache_misses;

/* Preserve M06/M08 saturated transform at far depth: plain upstream
   transform_map_vert_16 wraps at s16 and can create fake near walls. */
static s16 m11_sat16(s32 value) {
    return (s16)(value > 32767 ? 32767 : (value < -32768 ? -32768 : value));
}
static Vect2D_s16 m11_transform_saturated(s16 x,s16 y) {
    s16 tlx=x-playerXInt, tly=y-playerYInt;
    s32 rx=((s32)tlx*angleSin16)-((s32)tly*angleCos16);
    s32 ry=((s32)tlx*angleCos16)+((s32)tly*angleSin16);
    Vect2D_s16 v;
    v.x=m11_sat16(rx>>FIX16_FRAC_BITS);
    v.y=m11_sat16(ry>>(FIX16_FRAC_BITS-TRANS_Z_FRAC_BITS));
    return v;
}
/* Caches ONLY rigid camera-space transformations, not clipping/visibility.
   Inputs playerXInt/angleSin16 are set before portal_rend. The source map
   must stay unchanged during a frame. */
static void m11_load_cached_walls(u16 count, const u16 *ids,
                                   const vertex *verts, Vect2D_s16 *dest)
{
    if (!m11_vertex_xy || !m11_vertex_stamp) {
        load_transform_and_duplicate_verts(count, (u16*)ids, (vertex*)verts, dest);
        return;
    }
    for (u16 i=0; i+1<count; ++i) {
        u16 a=ids[i], b=ids[i+1];
        if (a >= cur_portal_map->num_verts || b >= cur_portal_map->num_verts) {
            load_transform_and_duplicate_verts(count, (u16*)ids, (vertex*)verts, dest);
            return;
        }
        if (m11_vertex_stamp[a] != m11_vertex_epoch) {
            m11_vertex_xy[a]=m11_transform_saturated(verts[a].x,verts[a].y);
            m11_vertex_stamp[a]=m11_vertex_epoch;
            m11_vertex_cache_misses++;
        } else m11_vertex_cache_hits++;
        if (m11_vertex_stamp[b] != m11_vertex_epoch) {
            m11_vertex_xy[b]=m11_transform_saturated(verts[b].x,verts[b].y);
            m11_vertex_stamp[b]=m11_vertex_epoch;
            m11_vertex_cache_misses++;
        } else m11_vertex_cache_hits++;
        dest[(i<<1)] = m11_vertex_xy[a];
        dest[(i<<1)+1] = m11_vertex_xy[b];
    }
}
"""
    source=source.replace(decl,decl+code,1)
    alloc='    sector_rendered_cache = man_malloc(sizeof(u8) * cur_portal_map->num_sectors, "sector visited cache");\n'
    if source.count(alloc)!=1: raise ValueError("portal init allocation changed")
    source=source.replace(alloc,alloc+'''    m11_vertex_xy = man_malloc(sizeof(Vect2D_s16)*cur_portal_map->num_verts, "M11 vertex transforms");
    m11_vertex_stamp = man_malloc(sizeof(u16)*cur_portal_map->num_verts, "M11 vertex epochs");
    if (m11_vertex_stamp) memset(m11_vertex_stamp,0,sizeof(u16)*cur_portal_map->num_verts);
''',1)
    cleanup='    man_free(sector_rendered_cache, "sector visited cache");\n'
    if source.count(cleanup)!=1: raise ValueError("portal cleanup changed")
    source=source.replace(cleanup,cleanup+'''    if (m11_vertex_stamp) man_free(m11_vertex_stamp, "M11 vertex epochs");
    if (m11_vertex_xy) man_free(m11_vertex_xy, "M11 vertex transforms");
    m11_vertex_stamp=0; m11_vertex_xy=0;
''',1)
    transform="    load_transform_and_duplicate_verts(num_walls+1, &map->walls[wall_offset], map->vertexes, transformed_vert_buffer);\n"
    if source.count(transform)!=1: raise ValueError("visit_graph transform call changed")
    source=source.replace(transform,'    m11_load_cached_walls(num_walls+1, &map->walls[wall_offset], map->vertexes, transformed_vert_buffer);\n',1)
    entry='void portal_rend(u16 src_sector, u32 cur_frame) {\n'
    if source.count(entry)!=1: raise ValueError("portal_rend entry changed")
    source=source.replace(entry,entry+'''    if (++m11_vertex_epoch == 0) {
        if (m11_vertex_stamp) memset(m11_vertex_stamp,0,sizeof(u16)*cur_portal_map->num_verts);
        m11_vertex_epoch=1;
    }
    m11_vertex_cache_hits=0;
    m11_vertex_cache_misses=0;
''',1)
    p.write_text(source)
    print("M11 vertex cache: 6 bytes per vertex; fresh clip buffer per portal visit")


def skip_fully_occluded_portals(out):
    """M11 A/B: conservative early-out for a completely filled clip window.

    The renderer cannot draw new pixels once every yclip column has top>=bot.
    The test costs O(window width); use only beyond the first portal depth,
    leaving source-sector drawing unchanged.
    """
    d=out/"src/draw.c"
    t=d.read_text()
    anchor="static u8* yclip;\n"
    if t.count(anchor)!=1: raise ValueError("draw.c yclip anchor changed")
    t=t.replace(anchor,anchor+"""
u8 manifold_window_fully_occluded(u16 lo, u16 hi) {
    if (!yclip || hi > RENDER_WIDTH || lo >= hi) return 0;
    for (u16 x=lo; x<hi; ++x) {
        if (yclip[(x<<1)] < yclip[(x<<1)+1]) return 0;
    }
    return 1;
}
""",1)
    d.write_text(t)
    p=out/"src/portal.c"
    c=p.read_text()
    entry="    if (x1 >= x2) return;\n"
    if c.count(entry)!=1: raise ValueError("portal early return anchor changed")
    c=c.replace(entry,entry+"""    if (depth >= 2 && manifold_window_fully_occluded(x1,x2)) { return; }
""",1)
    c=c.replace("#include <genesis.h>\n","#include <genesis.h>\nu8 manifold_window_fully_occluded(u16 lo, u16 hi);\n",1)
    p.write_text(c)
    print("M11 conservative occlusion: skip cells behind fully covered columns")


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
        if (is_portal && ceil_color != 0 /* outdoors sky is transparent */\n             && get_sector_group_ceil_color(sector_group(portal_sector, map)) != 0\n             && trans_v1.y > ({far}<<TRANS_Z_FRAC_BITS) && trans_v2.y > ({far}<<TRANS_Z_FRAC_BITS)) {{
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

def m13_sky_merge_upper_wall(out):
    """M13.2 DOOM sky-to-sky portal: suppress spurious upper wall.

    The emitter tags high color 0xFE only when both sector ceiling flats
    are F_SKY1. This branch must be tested independently of BSP precision.
    The branch now draws sky ceiling into the old upper-wall screen region.
    """
    p=out/"src/portal.c";s=p.read_text()
    old="            if(neighbor_ceil_height < ceil_height) {"
    new="""            if(neighbor_ceil_height < ceil_height &&
               map->wall_colors[(portal_idx<<WALL_COLOR_NUM_PARAMS_SHIFT)+WALL_HIGH_COLOR_IDX] != 0xFE) {"""
    if s.count(old)!=2:
        raise ValueError("M13 sky merge: expected two upper-step branches")
    p.write_text(s.replace(old,new,2))
    print("M13 DOOM sky merging: upper walls suppressed on F_SKY1/F_SKY1 portals")

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

def hud_fps_and_build_tag(out):
    """M13: show FPS and the ROM name on the black band under the HUD bar
    (BG_B row 26), not in the top border. The counter is text on the
    background plane, not a sprite, so it does not touch the 3D view.
    showStats() is replaced whole so it does not depend on earlier layouts.
    MANIFOLD_BUILD_TAG (set by the workflow) is the label, e.g. CLAUDIO M12 PLAY H40.
    """
    tag=os.environ.get("MANIFOLD_BUILD_TAG","MANIFOLD").upper()
    if len(tag)>28 or any(not (32<=ord(ch)<127) or ch in '"\\' for ch in tag):
        raise ValueError(f"bad MANIFOLD_BUILD_TAG: {tag!r}")
    g=out/"src/game.c"; s=g.read_text()
    start=s.find("void showStats() {")
    if start<0: raise ValueError("showStats not found")
    end=s.find("\n}\n",start)
    if end<0: raise ValueError("showStats end not found")
    end+=3
    new=f'''#define MANIFOLD_BUILD_TAG "{tag}"
static void manifold_hud_text(const char *t, u16 x, u16 y) {{
    while (*t) {{
        VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL3, 1, 0, 0, TILE_FONT_INDEX + (*t) - 32), x++, y);
        t++;
    }}
}}

/* M13: FPS (left) and ROM name (right) on row 26, under the HUD bar.
   Row 27 is outside the visible 224-line frame in H40, so it is not used. */
void showStats() {{
    char num[16];
    fix32ToStr(SYS_getFPSAsFloat(), num, 1);
    VDP_clearTileMapRect(BG_B, 0, 26, 40, 1);
    manifold_hud_text("FPS ", 1, 26);
    manifold_hud_text(num, 5, 26);
    u16 tag_len = strlen(MANIFOLD_BUILD_TAG);
    manifold_hud_text(MANIFOLD_BUILD_TAG, 39 - tag_len, 26);
}}
'''
    s=s[:start]+new+s[end:]
    g.write_text(s)
    print(f"FPS on HUD band, build tag {tag!r}")

def m13_werk_hud_timing(out):
    """Experimental H40 A/B for incomplete HUD at normal CPU speed.

    User observation: BlastEm overclock displays complete HUD; normal speed
    misses tiles. Preload the initial Doom face and compose the complete
    status bar in init, before the first renderer frame. Keep per-frame
    updates only for changed state; stop clearing/repainting the whole FPS
    text band on every frame. Not a blanket VDP timing fix.
    """
    p=out/"src/doom_statusbar.c"
    if not p.exists():
        raise ValueError("M13 HUD timing requires MANIFOLD_HUD=doom")
    s=p.read_text()
    old="""    dhud_have_hash = 0;
    dhud_draw_margins();
    return free_tile_loc + doom_hud_vram_count;"""
    new="""    /* M13 Werk: finish static HUD + initial face before renderer starts.
       CPU transfer here avoids SGDK's still-unflushed DMA queue. */
    VDP_loadTileData((const u32 *)hudw_faces[dhud_face.index],
                     manifold_hud_base + HUDW_FACE_SLOT, 16, CPU);
    dhud_face.shown = dhud_face.index;
    dhud_draw_margins();
    dhud_draw_bar();
    dhud_last_hash = HUDW_Hash(&dhud_state);
    dhud_have_hash = 1;
    return free_tile_loc + doom_hud_vram_count;"""
    if s.count(old)!=1:
        raise ValueError("M13 HUD initialization layout changed")
    p.write_text(s.replace(old,new,1))
    p=out/"src/game.c";s=p.read_text()
    old="""    VDP_clearTileMapRect(BG_B, 0, 26, 40, 1);
    manifold_hud_text("FPS ", 1, 26);
    manifold_hud_text(num, 5, 26);
    u16 tag_len = strlen(MANIFOLD_BUILD_TAG);
    manifold_hud_text(MANIFOLD_BUILD_TAG, 39 - tag_len, 26);"""
    new="""    static u8 m13_tag_written = 0;
    static char m13_last_fps[16] = "";
    if (!m13_tag_written) {
        VDP_clearTileMapRect(BG_B, 0, 26, 40, 1);
        manifold_hud_text("FPS ", 1, 26);
        u16 tag_len = strlen(MANIFOLD_BUILD_TAG);
        manifold_hud_text(MANIFOLD_BUILD_TAG, 39 - tag_len, 26);
        m13_tag_written = 1;
    }
    if (strcmp(m13_last_fps, num) != 0) {
        /* Only changed digits; clear a fixed 8-character FPS region. */
        manifold_hud_text("        ", 5, 26);
        manifold_hud_text(num, 5, 26);
        strcpy(m13_last_fps, num);
    }"""
    if s.count(old)!=1:
        raise ValueError("M13 FPS tag layout changed")
    p.write_text(s.replace(old,new,1))
    print("M13 Werk HUD timing: initial face/bar in init, FPS/tag only on changes")

def m13_werk_hud_vram_repair(out):
    """M13.1 VRAM diagnosis: periodically reload static Doom HUD tile graphics.

    Eight 32-byte tiles per game update, CPU mode, no DMA queue. All tile IDs
    stay fixed, without reloading the BG_B tilemap. This isolates whether
    the observed overclock-sensitive missing rectangles are caused by
    incomplete/corrupted VRAM tile patterns rather than the tilemap.
    """
    p=out/"src/doom_statusbar.c"
    if not p.exists():
        raise ValueError("HUD tile repair requires the Doom HUD")
    s=p.read_text()
    hook="void doom_hud_update(void) {"
    if s.count(hook)!=1:
        raise ValueError("M13 HUD update entry changed")
    added="""static u16 m13_hud_upload_cursor = 0;
static void m13_hud_replay_tiles(void) {
    /* HUDW_NTILES static tiles; face slot is managed separately. */
    if (m13_hud_upload_cursor >= HUDW_NTILES)
        m13_hud_upload_cursor = 0;
    u16 count = HUDW_NTILES - m13_hud_upload_cursor;
    if (count > 8) count = 8;
    VDP_loadTileData((const u32 *)hudw_tiles[m13_hud_upload_cursor],
                     manifold_hud_base + m13_hud_upload_cursor,
                     count, CPU);
    m13_hud_upload_cursor += count;
}
"""
    s=s.replace(hook,added+hook+"\n    m13_hud_replay_tiles();",1)
    p.write_text(s)
    print("M13 Werk VRAM HUD diagnostic: replay 8 static tiles each game update")

def m13_werk_static_repair_once(out):
    """One-time, small VRAM refresh of HUD and sky; no HInt/VInt masking."""
    p=out/"src/doom_statusbar.c"; s=p.read_text()
    anchor="void doom_hud_update(void) {"
    if s.count(anchor)!=1: raise ValueError("HUD update changed")
    helper="""static u16 hud_repair_pos;
static void hud_repair_once(void) {
    if (hud_repair_pos >= HUDW_NTILES) return;
    u16 n = HUDW_NTILES - hud_repair_pos;
    if (n > 8) n = 8;
    VDP_loadTileData((const u32 *)hudw_tiles[hud_repair_pos],
                     manifold_hud_base + hud_repair_pos, n, CPU);
    hud_repair_pos += n;
}
"""
    s=s.replace(anchor,helper+anchor+"\n    hud_repair_once();",1)
    p.write_text(s)
    p=out/"src/manifold_sky.c";s=p.read_text()
    anchor="void manifold_sky_update(void) {"
    if s.count(anchor)!=1: raise ValueError("sky update changed")
    helper="""static u16 sky_repair_pos;
static void sky_repair_once(void) {
    if (!sky_ready || sky_repair_pos >= SKY_REPAIR_TILE_COUNT) return;
    u16 n = SKY_REPAIR_TILE_COUNT - sky_repair_pos;
    if (n > 4) n = 4;
    for (u16 k=0; k<n; ++k) {
        u16 i=sky_repair_pos+k;
        VDP_loadTileData(&sky_tiles[i*8], sky_index[i], 1, CPU);
    }
    sky_repair_pos += n;
}
"""
    import re
    m=re.search(r"static const u32 sky_tiles\[(\d+)\*8\]",s)
    if not m: raise ValueError("sky array declaration changed")
    s=s.replace(anchor,helper.replace("SKY_REPAIR_TILE_COUNT",m.group(1))+anchor+"\n    sky_repair_once();",1)
    p.write_text(s)
    print("M13 one-time HUD/sky VRAM recovery, no interrupt masking")

def m14_identity(out):
    """M14 rule: every test ROM carries its name/purpose in the cartridge
    header (BlastEm shows it in the window title) and opens on a black SGDK
    text screen with the ROM name, what it tests and
    'START or wait 15 s'.  MANIFOLD_ROM_NAME (<=48 chars, header + title),
    MANIFOLD_ROM_TEST ('|' separates lines of <=38 chars)."""
    import re as _re
    name=os.environ.get("MANIFOLD_ROM_NAME","").strip()
    if not name: return
    clean=lambda t:_re.sub(r'[^A-Za-z0-9 ._:+/()=%,-]','',t)
    name=clean(name)[:48]
    test=[clean(x)[:38] for x in os.environ.get("MANIFOLD_ROM_TEST","").split("|") if x.strip()]
    h=out/"src"/"rom_header.c"
    # the makefile copies SGDK's template only when src/rom_header.c is absent
    note=clean(os.environ.get("MANIFOLD_ROM_TEST","").split("|")[0] if os.environ.get("MANIFOLD_ROM_TEST") else "MANIFOLD E1M1")[:40]
    h.write_text("""#include <genesis.h>

__attribute__((externally_visible))
const ROMHeader rom_header = {
#if (MODULE_MEGAWIFI  && (MEGAWIFI_IMPLEMENTATION & MEGAWIFI_IMPLEMENTATION_MW_CART))
    "SEGA MEGAWIFI   ",
#elif (ENABLE_BANK_SWITCH != 0)
    "SEGA SSF        ",
#else
    "SEGA MEGA DRIVE ",
#endif
    "(C)SGDK 2026    ",
    "%s",
    "%s",
    "GM 00000000-00",
    0x000,
    "JD              ",
    0x00000000,
#if (ENABLE_BANK_SWITCH != 0)
    0x003FFFFF,
#else
    0x000FFFFF,
#endif
    0xE0FF0000,
    0xE0FFFFFF,
    "RA",
    0xF820,
    0x00200000,
    0x0020FFFF,
    "            ",
    "%s",
    "JUE             "
};
""" % (name.ljust(48), name.ljust(48), note.ljust(40)))
    lines=["MD-DOOM64KB MANIFOLD E1M1","",name]+[""]+test
    cl=",\n".join('    "%s"'%l for l in lines)
    m=out/"src"/"main.c";t=m.read_text()
    fn=f"""
static const char* const m14_splash_lines[] = {{
{cl}
}};
static void m14_splash(void) {{
    PAL_setColor(0, 0x000);
    PAL_setColor(15, 0xEEE);
    VDP_setTextPalette(PAL0);
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    u16 n = sizeof(m14_splash_lines) / sizeof(m14_splash_lines[0]);
    for (u16 i = 0; i < n; i++) VDP_drawText(m14_splash_lines[i], 1, 2 + i);
    VDP_drawText("PRESS START OR WAIT 15 SECONDS", 1, 22);
    char buf[8];
    u16 start_seen = 0;
    for (u16 f = 0; f < 900; f++) {{
        if (f % 60 == 0) {{
            intToStr(15 - f / 60, buf, 2);
            VDP_drawText("STARTING IN        ", 1, 24);
            VDP_drawText(buf, 13, 24);
        }}
        if (JOY_readJoypad(JOY_1) & BUTTON_START) {{ start_seen = 1; break; }}
        SYS_doVBlankProcess();
    }}
    if (start_seen) while (JOY_readJoypad(JOY_1) & BUTTON_START) SYS_doVBlankProcess();
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_waitDMACompletion();
}}
"""
    assert t.count("int main() {\n\tVDP_init();")==1
    t=t.replace("int main() {\n\tVDP_init();",fn+"\nint main() {\n\tVDP_init();\n\tm14_splash();")
    m.write_text(t)
    print("M14 identity:",name,"| splash lines",len(lines))

def m14_nohud(out):
    """M14 diagnostic: no Doom HUD and no FPS/title text (no per-frame VDP
    writes from the main loop except the sky and the queued sprite/palette DMA)."""
    g=out/"src"/"game.c";t=g.read_text()
    assert t.count("    showStats();\n")==1
    g.write_text(t.replace("    showStats();\n","    /* M14 NOHUD: showStats(); */\n"))
    h=out/"src"/"doom_statusbar.c";t=h.read_text()
    old="void doom_hud_update(void) {\n    hud_repair_once();"
    assert t.count(old)==1
    t=t.replace(old,"void doom_hud_update(void) {\n    return;\n    hud_repair_once();")
    old2="    dhud_draw_margins();\n    dhud_draw_bar();\n    dhud_last_hash"
    assert t.count(old2)==1
    t=t.replace(old2,"    dhud_last_hash")
    h.write_text(t)
    print("M14 NOHUD: HUD and FPS text disabled")

def m14_vdp_safe(out, mode=1):
    """M14: main-thread VDP writes race with the H-Int/V-Int handlers.

    A VDP command is two control-port words; an interrupt that writes the
    control port between them (H-Int register writes every frame, V-Int DMA
    queue flush) makes the VDP take the wrong address, so tile data / name
    table words land in the wrong VRAM place. The window is tiny, so the
    screen breaks only after minutes (FPS text, Doom face, status bar and
    sky update in the main loop).  SGDK documents this (sys.h): VDP access
    outside interrupts must be bracketed by SYS_disableInts/SYS_enableInts.
    Each statement is wrapped on its own, so interrupts stay masked for a
    few hundred cycles at a time.
    """
    import re
    pat=re.compile(r"^(\s*)((?:VDP_setTileMapXY|VDP_setTileMapDataRect|VDP_clearTileMapRect|VDP_loadTileData|SKY_CLEAR_BORDERS)\(.*\);)\s*$")
    total=0
    for name in ("game.c","doom_statusbar.c","manifold_sky.c"):
        p=out/"src"/name
        if not p.is_file(): continue
        lines=p.read_text().split("\n");n=0
        for i,l in enumerate(lines):
            m=pat.match(l)
            if m:
                if mode==2:
                    lines[i]=f"{m.group(1)}M14_VB_BEGIN(); {m.group(2)} M14_VB_END();";n+=1
                else:
                    lines[i]=f"{m.group(1)}SYS_disableInts(); {m.group(2)} SYS_enableInts();";n+=1
        if mode==2 and n:
            hdr=("#include <genesis.h>\n"
                 "/* M14 VBLANK-only VDP writes: H-Int never fires in vblank, so no H-Int can land between the two\n"
                 "   control-port words and the H-Int phase timing is not delayed by masking in the active area. */\n"
                 "static inline void m14_vb_begin(void){ for(;;){ SYS_disableInts(); if (*(volatile u16*)0xC00004 & 8) return; SYS_enableInts(); __asm__ volatile(\"nop\\n nop\\n nop\\n nop\"); } }\n"
                 "#define M14_VB_BEGIN() m14_vb_begin()\n#define M14_VB_END() SYS_enableInts()\n")
            lines.insert(0,hdr)
        p.write_text("\n".join(lines));total+=n
        print(f"M14 VDP safe: {name} wrapped {n} statements")
    if total<8: raise ValueError("M14 VDP safe: too few statements wrapped")

def m13_werk_vdp_atomic(out):
    """M13.1 A/B: keep V-Int bitmap DMA and H-Int register writes from
    interrupting SGDK multiwrite VDP operations on HUD/sky.

    Interrupt masking is ONLY around the static initialization copies,
    HUD row tilemaps and sky's once-per-angle BG_B update. No recurring
    HUD replay, no changes to renderer/viewport/SGDK or main VBlank DMA.
    """
    p=out/"src/doom_statusbar.c"
    if not p.is_file(): raise ValueError("M13 atomic needs Doom HUD")
    s=p.read_text()
    src="    VDP_loadTileData((const u32 *)hudw_tiles, manifold_hud_base, HUDW_NTILES, CPU);"
    dst="    VDP_waitDMACompletion();\n    SYS_disableInts(); /* M13: no HInt/VInt during initial HUD VRAM work */\n"+src
    if s.count(src)!=1: raise ValueError("M13 HUD upload missing")
    s=s.replace(src,dst,1)
    src="    return free_tile_loc + doom_hud_vram_count;"
    if s.count(src)!=1: raise ValueError("M13 HUD init return missing")
    s=s.replace(src,"    SYS_enableInts();\n"+src,1)
    # A changed HUD can involve several BG_B rows: guard the tilemap
    # sequence while leaving status calculation outside the critical region.
    src="static void dhud_draw_bar(void) {\n"
    if s.count(src)!=1: raise ValueError("M13 HUD row function missing")
    s=s.replace(src,src+"    SYS_disableInts();\n",1)
    src="        VDP_setTileMapDataRect(BG_B, dhud_row, DHUD_X, DHUD_Y + r, HUDW_COLS, 1, HUDW_COLS, CPU);\n    }\n}"
    if s.count(src)!=1: raise ValueError("M13 HUD row end missing")
    s=s.replace(src,src[:-1]+"    SYS_enableInts();\n}",1)
    # Important: init already masks interrupts; don't nest nested
    # SYS_disableInts/SYS_enableInts in dhud_draw_bar during init.
    # The init-time bar uses the same function, so temporarily keep
    # the masking solely on the short row update and make the init
    # sequence one large but non-nested critical section.
    s=s.replace("    SYS_disableInts();\n    for (u8 r = 0; r < HUDW_ROWS; r++) {",
                "    if (!m13_init_atomic) SYS_disableInts();\n    for (u8 r = 0; r < HUDW_ROWS; r++) {",1)
    s=s.replace("    SYS_enableInts();\n}\n\nstatic void dhud_draw_margins",
                "    if (!m13_init_atomic) SYS_enableInts();\n}\n\nstatic void dhud_draw_margins",1)
    src="static u16 manifold_hud_base;"
    if s.count(src)!=1: raise ValueError("M13 HUD base missing")
    s=s.replace(src,"static u8 m13_init_atomic = 0;\n"+src,1)
    src="    SYS_disableInts(); /* M13: no HInt/VInt during initial HUD VRAM work */"
    s=s.replace(src,src+"\n    m13_init_atomic = 1;",1)
    src="    SYS_enableInts();\n    return free_tile_loc + doom_hud_vram_count;"
    if s.count(src)!=1: raise ValueError("M13 HUD final critical end missing")
    s=s.replace(src,"    m13_init_atomic = 0;\n"+src,1)
    p.write_text(s)

    p=out/"src/manifold_sky.c"
    s=p.read_text()
    import re
    src=re.search(r"    for \(u16 k = 0; k < \d+; k\+\+\) \{",s)
    if not src: raise ValueError("M13 sky tile loop missing")
    s=s[:src.start()]+"    VDP_waitDMACompletion();\n    SYS_disableInts(); /* M13 sky initial VRAM upload + BG_B */\n"+s[src.start():]
    src="    sky_ready = 1; sky_last = -1;"
    if s.count(src)!=1: raise ValueError("M13 sky init final missing")
    s=s.replace(src,"    SYS_enableInts();\n"+src,1)
    src="    sky_last = off;"
    if s.count(src)!=1: raise ValueError("M13 sky update anchor missing")
    s=s.replace(src,src+"\n    SYS_disableInts(); /* M13 per-angle BG_B tilemap writes */",1)
    src=re.search(r"    SKY_CLEAR_BORDERS\(\d+, \d+\);",s[s.index("    sky_last = off;"):])
    if not src: raise ValueError("M13 sky update end missing")
    ix=s.index("    sky_last = off;")+src.end()
    s=s[:ix]+"\n    SYS_enableInts();"+s[ix:]
    p.write_text(s)
    print("M13 Werk VDP atomic: HUD+sky main-thread writes protected from bitmap interrupts")

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

def h32_mode(out):
    """MANIFOLD_H32=1: H32 (256 px) screen, 3D rendered on columns 2..61
    (240 px, 8 px black border each side, upstream H32_MODE path), HUD bar
    full width without stone margins, smaller VBlank DMA batches."""
    cfg=out/"src/config.h"; cs=cfg.read_text()
    if "//#define H32_MODE" not in cs: raise ValueError("config.h H32 switch changed")
    cfg.write_text(cs.replace("//#define H32_MODE","//#define H32_MODE (upstream path needs pvs_scan, not used)\n#define MANIFOLD_H32 1",1))
    g=out/"src/game.c"; gs=g.read_text()
    o="    #else \n    VDP_setScreenWidth320();\n    #endif\n"
    if o not in gs: raise ValueError("screen width switch changed")
    g.write_text(gs.replace(o,"    #else \n    VDP_setScreenWidth256();   /* MANIFOLD_H32 */\n    #endif\n",1))
    pc=out/"src/portal.c"; ps=pc.read_text()
    o="            visit_graph(src_sector, src_sector, 0, RENDER_WIDTH, cur_frame, 0);\n"
    if ps.count(o)!=1: raise ValueError("portal_rend window changed")
    pc.write_text(ps.replace(o,"            visit_graph(src_sector, src_sector, 2, RENDER_WIDTH-2, cur_frame, 0);   /* H32: 240 px view */\n",1))
    for f in ("manifold_sky.c","doom_statusbar.c","my_bmp.c"):
        q=out/"src"/f
        if q.exists():
            q.write_text('#include "config.h"\n'+q.read_text())
    b=out/"src/my_bmp.c"; bs=b.read_text()
    if "#define NTSC_TILES_BW           7\n" not in bs: raise ValueError("bmp DMA batch changed")
    b.write_text(bs.replace("#define NTSC_TILES_BW           7\n","#define NTSC_TILES_BW           5   /* H32: ~20% less DMA per blank line */\n",1))
    print("H32 mode: 240px view, H32 screen")

def install_doom_hud(out, wad):
    """M10 (MANIFOLD_HUD=doom): replace Manifold's inventory HUD rendering with
    the R128 HUD-WAD status bar. Inventory logic (keys) is kept."""
    import shutil, subprocess, sys as _sys
    root=Path(__file__).resolve().parents[3]
    m10=Path(__file__).resolve().parents[1]/"m10"
    hdr=out/"src/hud_wad_assets.h"
    subprocess.run([_sys.executable,str(m10/"gen_hud_manifold.py"),"--wad",str(wad),"--out",str(hdr)],check=True)
    _sys.path.insert(0,str(m10))
    import gen_hud_manifold
    gen_hud_manifold.single_palette(str(hdr))
    # SGDK provides uint8_t & co. as macros; no libc <stdint.h> in the m68k-elf kit
    (out/"src/hud_wad_logic.h").write_text((root/"src/hud_wad_logic.h").read_text().replace("#include <stdint.h>",""))
    hdr.write_text(hdr.read_text().replace("#include <stdint.h>",""))
    shutil.copy(m10/"doom_statusbar.c",out/"src/doom_statusbar.c")
    inv=out/"src/inventory.c"
    s=inv.read_text()
    old_init_start="    u32 new_free_tile_loc = load_inventory_items_to_vram(free_tile_loc);\n"
    old_init_end="    inventory_reset();\n    return new_free_tile_loc;\n"
    a=s.index(old_init_start); b=s.index(old_init_end,a)
    s=s[:a]+"    u32 new_free_tile_loc = doom_hud_init(free_tile_loc);\n"+s[b:]
    old_draw="void inventory_draw() {\n"
    if s.count(old_draw)!=1: raise ValueError("inventory_draw changed")
    s=s.replace(old_draw,old_draw+"    doom_hud_update();\n    return;\n",1)
    s=s.replace('#include "inventory.h"\n','#include "inventory.h"\nu32 doom_hud_init(u32 free_tile_loc);\nvoid doom_hud_update(void);\n',1)
    inv.write_text(s)
    print("doom HUD installed (R128 HUD-WAD)")

def install_sky(out, res):
    """SKY1 band on BG_B behind the framebuffer (BG_A colour 0 = sky
    ceilings), 256px wide like Doom (90 degrees), tiles stored in VRAM
    reclaimed from the unused WINDOW nametable and the never-displayed
    rows 28-63 of the 64x64 BG_B nametable (~272 tiles)."""
    import wad_textures as WT
    sky_png=Path(__file__).with_name("sky_e1doom_256x72_pal.png")      # user-made 256x72 grey sky, vertical-line dither (r064)
    if sky_png.exists() and os.environ.get("MANIFOLD_SKY_PNG","1")=="1":
        from PIL import Image
        _im=Image.open(sky_png).convert("RGB"); _yo=0
        res=dict(res,sky=(256,72,[[_im.getpixel((x,_yo+y)) for x in range(256)] for y in range(72)]))
        sk=WT.sky_tiles(res, band_rows=9, band_cols=32, max_tiles=131, merge=True, pair=True, neutral=True)
    else:
        sk=WT.sky_tiles(res, band_rows=9, band_cols=32, max_tiles=131, merge=True)
    n=len(sk["tiles"]);rows=sk["rows"];cols=sk["cols"]
    tiles=",\n".join("  "+",".join(f"0x{v:08x}" for v in t) for t in sk["tiles"])
    tmap=",".join(str(v) for row in sk["map"] for v in row)
    band_top=4   # Doom: sky texture top at the top of the view, mountains reach the horizon
    c=f"""#include "manifold_mute_klog.h"
#include <genesis.h>
#include "game.h"
/* GENERATED: Doom SKY1 band, 3D palette (PAL1) */
#ifdef MANIFOLD_H32
#define SKY_X0 0
#define SKY_CLEAR_BORDERS(y, h) do {{ VDP_clearTileMapRect(BG_B, 0, (y), 1, (h)); VDP_clearTileMapRect(BG_B, 31, (y), 1, (h)); }} while (0)
#else
#define SKY_X0 4
#define SKY_CLEAR_BORDERS(y, h) do {{ }} while (0)
#endif
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
        VDP_setTileMapDataRect(BG_B, sky_row_buf, SKY_X0, 4 + r, 32, 1, 32, CPU);
        SKY_CLEAR_BORDERS(4 + r, 1);
    }}
    sky_ready = 1; sky_last = -1;
    return free_tile_loc;
}}
void manifold_sky_update(void) {{
    if (!sky_ready) return;
    s16 off = (s16)((cur_player_pos.ang >> 3) & {cols - 1});   /* 1024 ang = 360 deg: 256 ang = 90 deg = 32 tiles = one 256px sky, same speed as the walls */
    if (off == sky_last) return;
    sky_last = off;
    for (u16 r = 0; r < {rows}; r++)
        for (u16 c = 0; c < 32; c++)
            sky_row_buf[r*32 + c] = TILE_ATTR_FULL(PAL1, 0, 0, 0, sky_index[sky_map[r][(c - off) & {cols - 1}]]);
    VDP_setTileMapDataRect(BG_B, sky_row_buf, SKY_X0, {band_top}, 32, {rows}, 32, CPU);
    SKY_CLEAR_BORDERS({band_top}, {rows});
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

def install_e1m1_music(out):
    """Add the existing R128 E1M1 VGM arrangement to Manifold's XGM driver.

    Music is opt-in for comparison. Runtime staging never modifies the R128.
    VGM is restored by prepare_r25_music.py in the disposable runner workspace.
    """
    vgm=Path(os.environ["MANIFOLD_MUSIC_VGM"])
    if not vgm.is_file() or vgm.stat().st_size<1024:
        raise ValueError(f"R128 E1M1 music VGM missing: {vgm}")
    res=out/"res"
    (res/"manifold_e1m1.vgm").write_bytes(vgm.read_bytes())
    target=res/"music_res.res"
    if not target.is_file() or target.read_text().strip():
        raise ValueError("Expected empty Manifold music_res.res, refusing overwrite")
    target.write_text('XGM bgm_e1m1 "manifold_e1m1.vgm"\n')
    p=out/"src/game.c"
    src=p.read_text()
    anchor="    MEM_dump();"
    if src.count(anchor)!=1: raise ValueError("Manifold init_game music start anchor changed")
    src=src.replace(anchor,anchor+"""
    /* M11 music variant: E1M1 starts only after Z80 PCM setup and stage load.
       XGM driver plays in the background; no per-render or frame FM writes. */
    if (music_on) { extern const u8 *const m14_bgm; XGM_startPlay(m14_bgm); }
""",1)
    p.write_text(src)
    # per-map music: the pointer lives in its own object (pinned by the split linker script),
    # so the common game code does not reference the map-specific bgm symbol
    (out/"src/m14_bgm.c").write_text('#include <genesis.h>\n#include "../res/music_res.h"\nconst u8 *const m14_bgm = bgm_e1m1;\n')
    print("M11 music: E1M1 classic XGM started after game init, source",vgm.name)



def m11_safe_near_clipping(out):
    """M11: guard reciprocal lookup and interpolate crossing near plane in s32.

    Prior code reads z_recip_table_16[y>>4] even for negative y, BEFORE
    checking the clip status. Near clipping also subtracts x/z in s16 and
    can overflow on long E1M1 walls; fix the overflowing interpolation only.
    """
    p=out/"src/portal.c"
    c=p.read_text()
    old="""        u16 z_recip_v1 = z_recip_table_16[trans_v1.y>>TRANS_Z_FRAC_BITS];
        u16 z_recip_v2 = z_recip_table_16[trans_v2.y>>TRANS_Z_FRAC_BITS];"""
    if c.count(old)!=1:
        raise ValueError("portal primary reciprocal lookup changed")
    new="""        /* Guard negative depth *before* indexing the reciprocal LUT.
           Near-z-culled portals still use the special fallback below. */
        u16 z_recip_v1 = z_recip_table_16[(trans_v1.y < NEAR_Z_FIX ? NEAR_Z_FIX : trans_v1.y)>>TRANS_Z_FRAC_BITS];
        u16 z_recip_v2 = z_recip_table_16[(trans_v2.y < NEAR_Z_FIX ? NEAR_Z_FIX : trans_v2.y)>>TRANS_Z_FRAC_BITS];"""
    c=c.replace(old,new,1)
    # Another dormant rendering path contains the same out-of-bounds lookup.
    old2="""            u16 z_recip_v1 = z_recip_table_16[trans_v1.y>>TRANS_Z_FRAC_BITS];
            u16 z_recip_v2 = z_recip_table_16[trans_v2.y>>TRANS_Z_FRAC_BITS];"""
    if c.count(old2)!=1:
        raise ValueError("portal secondary reciprocal lookup changed")
    c=c.replace(old2,old2.replace("[trans_v1.y>>TRANS_Z_FRAC_BITS]","[(trans_v1.y < NEAR_Z_FIX ? NEAR_Z_FIX : trans_v1.y)>>TRANS_Z_FRAC_BITS]").replace("[trans_v2.y>>TRANS_Z_FRAC_BITS]","[(trans_v2.y < NEAR_Z_FIX ? NEAR_Z_FIX : trans_v2.y)>>TRANS_Z_FRAC_BITS]"),1)
    p.write_text(c)
    m=out/"src/math3d.c"
    t=m.read_text()
    left=t.index("    s16 dx = rx2-rx1;",t.index("    if(rz1_12_4 >= NEAR_Z_FIX && rz2_12_4 >= NEAR_Z_FIX)"))
    right=t.index("    // left near clip",left)
    chunk=t[left:right]
    replacement="""    /* Crosses the near plane: 32-bit interpolation only on clipped walls.
       The old s16 dx and reciprocal path overflowed for long E1M1 edges.
       The coordinates remain fixed-point 12.4 for depth and 16-bit for x. */
    s32 dx_near = (s32)rx2 - rx1;
    s32 dz_near = (s32)rz2_12_4 - rz1_12_4;
    if (dz_near == 0) return NEAR_Z_CULLED;
"""
    t=t[:left]+replacement+t[right:]
    # Match both endpoint blocks even when upstream has trailing spaces.
    import re
    t, clipped_count = re.subn(
        r"s32\s+x_adjust_10\s*=\s*dx_over_dz_6\s*\*\s*z_adjust_12_4;\s*(?://[^\n]*)?\s*s16\s+x_adjust_int\s*=\s*x_adjust_10\s*>>\s*\(6\+TRANS_Z_FRAC_BITS\);",
        "s32 x_adjust_int = (dx_near * (s32)z_adjust_12_4) / dz_near;",
        t)
    if clipped_count!=2:
        raise ValueError(f"Expected two near plane interpolation edits; got {clipped_count}")
    t=t.replace("""        rx1 += x_adjust_int;    // modify x coord""","""        rx1 = MANIFOLD_SAT16((s32)rx1 + x_adjust_int);  // near-plane intersection""")
    t=t.replace("""        rx2 += x_adjust_int;""","""        rx2 = MANIFOLD_SAT16((s32)rx2 + x_adjust_int);""")
    t=t.replace("""        rz1_12_4 = NEAR_Z_FIX;
        trans_v2->x = rx2;
        trans_v2->y = rz1_12_4;""","""        rz2_12_4 = NEAR_Z_FIX;
        trans_v2->x = rx2;
        trans_v2->y = rz2_12_4;""")
    if t.count("x_adjust_int = (dx_near * (s32)z_adjust_12_4) / dz_near")!=2:
        raise ValueError("near clipping both sides not patched")
    m.write_text(t)
    print("M11 near clipping: signed LUT guard; 32-bit intersection x; corrected right z")


def m11_hud_recompose_diagnostic(out):
    """Recompose BG_B bar every update to test tilemap corruption; may cost FPS."""
    p=out/"src/doom_statusbar.c"
    t=p.read_text()
    anchor="    u16 h = HUDW_Hash(&dhud_state);"
    if t.count(anchor)!=1: raise ValueError("M10 hash anchor changed")
    t=t.replace(anchor,"    dhud_draw_bar(); /* M11 diagnostic: rewrite BG_B HUD tilemap */\n"+anchor,1)
    p.write_text(t)
    print("M11 HUD tilemap recomposition diagnostic enabled")


def m11_hide_weapon_sprites_diagnostic(out):
    """Move hardware weapon sprites off-screen to isolate HUD black blocks."""
    p=out/"src/weapon_sprites.c"
    s=p.read_text()
    anchor="    VDP_updateSprites(cur_num_sprites, transfer_type);"
    if s.count(anchor)!=1: raise ValueError("weapon sprite transfer anchor changed")
    s=s.replace(anchor,"    for (u16 si=0; si<cur_num_sprites; ++si) VDP_setSpritePosition(sprite_idx_start+si, 0, 0);\n"+anchor,1)
    anchor2="    VDP_updateSprites(cur_num_sprites, DMA_QUEUE);"
    if s.count(anchor2)!=1: raise ValueError("weapon sprite offset anchor changed")
    s=s.replace(anchor2,"    for (u16 si=0; si<cur_num_sprites; ++si) VDP_setSpritePosition(sprite_idx_start+si, 0, 0);\n"+anchor2,1)
    p.write_text(s)
    print("M11 hardware weapon sprites moved off-screen (diagnostic)")

def fixed_camera_input(out, cells, lumps):
    """M11 controlled A/B: six repeatable views with NO joypad movement.

    Two exterior cameras are pinned from MAME #42850641871 frame traces.
    Three expensive step/bridge candidate cells are selected deterministically
    from floor-height transitions and portal fanout (diagnostic, not asserted
    to represent named WAD rooms). Last view is the actual player spawn.
    Camera switches every 300 VBlanks after frame 60, and is reasserted
    on each joy poll; test render does not affect the next camera position.
    """
    import math
    byid={c["id"]:c for c in cells}
    bysec={c["id"]:c["doom_sector"] for c in cells}
    for cell_id in (48,51):
        if cell_id not in byid: raise ValueError("Pinned external camera cell absent")
    def floor(c):
        return lumps["SECTORS"][bysec[c["id"]]][0]
    def centre(c):
        ps=[(w["a"][0]/16,w["a"][1]/16) for w in c["walls"]]
        return tuple(round(sum(p[d] for p in ps)/len(ps)) for d in (0,1))
    # S0/S1/B0 are *candidate* complexity views, selected by reproducible
    # topology metrics. Their position & sector IDs are logged in the build.
    rank=[]
    for c in cells:
        if c["id"] in (48,51): continue
        if lumps["SECTORS"][c["doom_sector"]][3].rstrip(b"\0")==b"F_SKY1": continue
        neighbors={w["neighbor"] for w in c["walls"] if w["neighbor"]>=0}
        height_changes=sum(abs(floor(byid[n])-floor(c))>=8 for n in neighbors)
        distinct={bysec[n] for n in neighbors}
        score=height_changes*8+len(distinct)*3+len(neighbors)
        rank.append((-score,c["id"],c))
    rank.sort()
    chosen=[]
    used_sectors=set()
    for _,_,c in rank:
        if c["doom_sector"] in used_sectors: continue
        chosen.append(c);used_sectors.add(c["doom_sector"])
        if len(chosen)==3: break
    if len(chosen)!=3: raise ValueError("Not enough stair/bridge candidates")
    spawns=[(x,y) for x,y,angle,type_id,flags in lumps["THINGS"] if type_id==1]
    if len(spawns)!=1: raise ValueError("Player1 spawn missing")
    sx,sy=spawns[0]
    initial=[c for c in cells if point_inside([w["a"] for w in c["walls"]],(sx*16,sy*16))]
    if len(initial)!=1: raise ValueError("Spawn cell ambiguous")
    pinned=[
      ("E0",1781,-3691,48,0x151),
      ("E1",2093,-3664,51,0x38b),
    ]
    generated=[(f"S{i}",*centre(c),c["id"],angle)
               for i,(c,angle) in enumerate(zip(chosen,(0,256,512)))]
    cameras=pinned+generated+[("R0",sx,sy,initial[0]["id"],0)]
    for label,x,y,ci,ang in cameras:
        c=byid[ci]
        if not point_inside([w["a"] for w in c["walls"]],(x*16,y*16)):
            raise ValueError(f"Fixed camera {label} at {x},{y} outside cell {ci}")
    arr=",".join("{%d,%d,%d,%d}" % (x,y,ci,ang)
                 for label,x,y,ci,ang in cameras)
    p=out/"src/manifold_mute_klog.h"
    p.write_text(p.read_text()+"\nu16 manifold_fixed_joy(u16 j);\n#define JOY_readJoypad(j) manifold_fixed_joy(j)\n")
    q=out/"src/joy_helper.c"
    q.write_text(q.read_text()+f"""
#include "game.h"
#include "portal_map.h"
#include "sector_group.h"
#include "level.h"
static const s16 m11_fixed_cameras[6][4]={{{arr}}};
volatile u16 m11_camera_index=0xffff;
u16 manifold_fixed_joy(u16 j) {{
    (void)(JOY_readJoypad)(j);
    u32 frame=vtimer;
    if (frame<60) return 0;
    u16 idx=(u16)(((frame-60)/300)%6);
    m11_camera_index=idx;
    cur_player_pos.x=FIX32(m11_fixed_cameras[idx][0]);
    cur_player_pos.y=FIX32(m11_fixed_cameras[idx][1]);
    cur_player_pos.cur_sector=m11_fixed_cameras[idx][2];
    cur_player_pos.ang=m11_fixed_cameras[idx][3];
    u16 g=sector_group(cur_player_pos.cur_sector,(portal_map*)cur_portal_map);
    cur_player_pos.z=(get_sector_group_floor_height(g)<<(FIX32_FRAC_BITS-4))+FIX32(64);
    return 0;
}}
""")
    print("M11 FIXED CAMERA TABLE (300 VBlank each after frame 60):",cameras)


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
        cur_player_pos.z = (get_sector_group_floor_height(g)<<(FIX32_FRAC_BITS-4)) + FIX32(64);
    }}
    return BUTTON_LEFT;
}}
"""
    j.write_text(code)
    print("tour points:",len(pts))

def player_radius_collision(out):
    """Keep the player PLAYER_RADIUS (16) away from solid walls and ledges it
    cannot climb. Root cause of the 'walls flicker when you touch them' bug:
    the map's collision_vertexes are the raw walls (upstream insets them in
    its editor), so a wall could get inside the 10-unit near plane, be
    NEAR_Z_CULLED as a whole and leave its columns undrawn; the two display
    buffers then alternate stale images. Also removes the x==wall ZERO DIVIDE."""
    p=out/"src/collision.c"
    s=p.read_text()
    sig="collision_result check_for_collision_radius(fix32 curx, fix32 cury, fix32 cur_z, fix32 newx, fix32 newy, f32 radius_sqr, u16 cur_sector) {\n"
    if s.count(sig)!=1: raise ValueError("radius collision signature changed")
    wrapper="#define MANIFOLD_SWEPT "+("0" if os.environ.get("MANIFOLD_SWEPT","1")=="0" else "1")+"\n"+"""
extern const u16 e1_block_offsets[] __attribute__((weak));
extern const s16 e1_block_segs[] __attribute__((weak));
extern const portal_map e1m1_map __attribute__((weak));
#define MANIFOLD_R 16
#define MANIFOLD_R2 (MANIFOLD_R*MANIFOLD_R)
static u32 manifold_seg_d2(s16 px, s16 py, const s16* s) {
    s16 ax = s[0], ay = s[1];
    s16 ex = s[2] - ax, ey = s[3] - ay;
    s16 dx = px - ax, dy = py - ay;
    s32 t = (s32)dx * ex + (s32)dy * ey;
    if (t <= 0) { return (u32)((s32)dx * dx + (s32)dy * dy); }
    if (t >= (s32)ex * ex + (s32)ey * ey) {
        s16 bx = px - s[2], by = py - s[3];
        return (u32)((s32)bx * bx + (s32)by * by);
    }
    s32 cr = (s32)dx * ey - (s32)dy * ex;
    if (cr < 0) { cr = -cr; }
    u32 q = (u32)cr / (u16)s[4];
    return q * q;
}
static s32 manifold_cross(s16 ox, s16 oy, s16 ax, s16 ay, s16 bx, s16 by) {
    return (s32)(ax - ox) * (by - oy) - (s32)(ay - oy) * (bx - ox);
}
/* swept test: the step (cx,cy)->(nx,ny) properly crosses the wall segment */
static u8 manifold_step_crosses(s16 cx, s16 cy, s16 nx, s16 ny, const s16* s) {
    s32 d1 = manifold_cross(s[0], s[1], s[2], s[3], cx, cy);
    s32 d2 = manifold_cross(s[0], s[1], s[2], s[3], nx, ny);
    if ((d1 > 0 && d2 > 0) || (d1 < 0 && d2 < 0) || (d1 == 0 && d2 == 0)) { return 0; }
    s32 d3 = manifold_cross(cx, cy, nx, ny, s[0], s[1]);
    s32 d4 = manifold_cross(cx, cy, nx, ny, s[2], s[3]);
    if ((d3 > 0 && d4 > 0) || (d3 < 0 && d4 < 0)) { return 0; }
    return 1;
}
static u8 manifold_radius_blocked(s16 cx, s16 cy, s16 nx, s16 ny, u16 sect) {
    const s16* s = &e1_block_segs[e1_block_offsets[sect] * 5];
    u16 n = e1_block_offsets[sect + 1] - e1_block_offsets[sect];
    for (; n; n--, s += 5) {
#if MANIFOLD_SWEPT
        if ((cx != nx || cy != ny) && manifold_step_crosses(cx, cy, nx, ny, s)) { return 1; }
#endif
        s16 lo = s[0] < s[2] ? s[0] : s[2], hi = s[0] < s[2] ? s[2] : s[0];
        if (nx < lo - MANIFOLD_R || nx > hi + MANIFOLD_R) { continue; }
        lo = s[1] < s[3] ? s[1] : s[3]; hi = s[1] < s[3] ? s[3] : s[1];
        if (ny < lo - MANIFOLD_R || ny > hi + MANIFOLD_R) { continue; }
        u32 dn = manifold_seg_d2(nx, ny, s);
        if (dn >= MANIFOLD_R2) { continue; }
        u32 dc = manifold_seg_d2(cx, cy, s);
        if (dc < MANIFOLD_R2 && dn >= dc) { continue; }   /* already inside: may only back away */
        return 1;
    }
    return 0;
}
static collision_result manifold_collision_inner(fix32 curx, fix32 cury, fix32 cur_z, fix32 newx, fix32 newy, f32 radius_sqr, u16 cur_sector);
collision_result check_for_collision_radius(fix32 curx, fix32 cury, fix32 cur_z, fix32 newx, fix32 newy, f32 radius_sqr, u16 cur_sector) {
    if (&e1m1_map && cur_portal_map == &e1m1_map) {
        s16 cx = F32_toInt(curx), cy = F32_toInt(cury);
        if (newx != curx && manifold_radius_blocked(cx, cy, F32_toInt(newx), cy, cur_sector)) { newx = curx; }
        s16 mx = F32_toInt(newx);
        if (newy != cury && manifold_radius_blocked(mx, cy, mx, F32_toInt(newy), cur_sector)) { newy = cury; }
    }
    return manifold_collision_inner(curx, cury, cur_z, newx, newy, radius_sqr, cur_sector);
}
"""
    s=s.replace(sig,wrapper+"static collision_result manifold_collision_inner(fix32 curx, fix32 cury, fix32 cur_z, fix32 newx, fix32 newy, f32 radius_sqr, u16 cur_sector) {\n",1)
    p.write_text(s)
    print("collision: player radius 16 vs solid walls and ledges")

def bsp_order_renderer(out):
    """MANIFOLD_BSP=1: visit every cell at most once per frame, in strict
    front-to-back order from Doom's own BSP tree, relying on the per-column
    clip spans (yclip) for occlusion instead of recursive portal windows.

    Why: with the recursive portal walk a cell is re-entered once per portal
    window that shows it (40-65 visits/frame in E1M1, each re-transforming the
    cell), and the walk gives up after 10 visits / on stack pressure, leaving
    the window undrawn. Undrawn spans show the other display buffer's old
    image: distant walls that blink and the big 'triangles' outdoors.
    Requires cells == BSP leaves (emitter turns the same-sector merge off).
    Remaining open spans (beyond BSP_FAR) are filled with the fog colour, so a
    frame can never contain stale pixels."""
    import re
    far=int(os.environ.get("MANIFOLD_FAR","1600"))
    p=out/"src/portal.c"
    s=p.read_text()
    a="    // if this sector has been visited 32 times, or is already being currently rendered, skip it\n"
    if s.count(a)!=1: raise ValueError("visit_graph cache anchor changed")
    s=s.replace(a,a+"    if (manifold_bsp_mode) goto manifold_bsp_enter;\n",1)
    a="    sector_rendered_cache[sector]++; // = cur_frame;\n"
    if s.count(a)!=1: raise ValueError("visit_graph cache increment changed")
    s=s.replace(a,"manifold_bsp_enter:\n"+a,1)
    a="visit_graph(src_sector, portal_sector,"
    if s.count(a)<4: raise ValueError("portal recursion sites changed")
    s=s.replace(a,"if (!manifold_bsp_mode) visit_graph(src_sector, portal_sector,")
    a="        u8 manifold_fogged = 0;\n        if (is_portal &&"
    if s.count(a)==1:
        s=s.replace(a,"        u8 manifold_fogged = 0;\n        if (!manifold_bsp_mode && is_portal &&",1)
    s,n=re.subn(r"(?m)^(\s*)visit_graph\(src_sector, src_sector, ([^,]+), ([^,]+), cur_frame, 0\);",
                r"\1manifold_bsp_render(src_sector, \2, \3, cur_frame);",s)
    if n<1: raise ValueError("portal_rend root call changed")
    decl="""
u8 manifold_bsp_mode = 0;
void manifold_bsp_render(u16 src_sector, u16 wmin, u16 wmax, u32 cur_frame);
"""
    a="void visit_graph(u16 src_sector, u16 sector, u16 x1, u16 x2, u32 cur_frame, uint8_t depth) {"
    if s.count(a)!=1: raise ValueError("visit_graph signature changed")
    s=s.replace(a,decl+a,1)
    s+=f"""
/* ---- BSP-ordered traversal (generated by stage_rom.py: bsp_order_renderer) ---- */
extern const s16 e1_bsp_nodes[] __attribute__((weak));
extern const u16 e1_bsp_num_nodes __attribute__((weak));
extern const portal_map e1m1_map __attribute__((weak));
u8 manifold_open_cols(u16 a, u16 b);
void manifold_fill_open(u16 a, u16 b);
#define BSP_FAR {far}
static u16 bsp_wmin, bsp_wmax, bsp_src;
static u32 bsp_frame;
volatile u16 manifold_bsp_cells;

static u8 bsp_done;
static u16 bsp_cell_x1, bsp_cell_x2;   /* column window for the next cell: open range ∩ its bbox */
static u16 bsp_open_x1, bsp_open_x2;
/* world-space half-planes through the player bounding the still-open columns */
static s16 bsp_rnx, bsp_rny, bsp_lnx, bsp_lny;
u8 manifold_open_range(u16 a, u16 b, s16* lo, s16* hi);
static void bsp_refresh_open(void) {{
    s16 lo, hi;
    /* columns only ever close during a frame: shrink the previous range */
    if (!manifold_open_range(bsp_open_x1, bsp_open_x2, &lo, &hi)) {{ bsp_done = 1; return; }}
    bsp_open_x1 = lo; bsp_open_x2 = hi + 1;
    lo = lo - (RENDER_WIDTH/2) - 1;
    hi = hi - (RENDER_WIDTH/2) + 2;
    /* view: rx = tx*S - ty*C, rz = tx*C + ty*S ; column-(W/2) = rx*(W/2)/rz
       right of column hi:  rx*(W/2) - hi*rz > 0 ;  left of column lo: rx*(W/2) - lo*rz < 0 */
    bsp_rnx = (RENDER_WIDTH/2) * angleSin16 - hi * angleCos16;
    bsp_rny = -(RENDER_WIDTH/2) * angleCos16 - hi * angleSin16;
    bsp_lnx = (RENDER_WIDTH/2) * angleSin16 - lo * angleCos16;
    bsp_lny = -(RENDER_WIDTH/2) * angleCos16 - lo * angleSin16;
}}

/* exact = also test the individual columns (worth it before a cell visit) */
static u8 bsp_box_visible(const s16* bb, u8 exact) {{   /* top, bottom, left, right */
    s16 xs0 = bb[2] - playerXInt, xs1 = bb[3] - playerXInt;
    s16 ys0 = bb[1] - playerYInt, ys1 = bb[0] - playerYInt;
    bsp_cell_x1 = bsp_open_x1; bsp_cell_x2 = bsp_open_x2;
    if (xs0 <= 0 && xs1 >= 0 && ys0 <= 0 && ys1 >= 0) {{ return 1; }}
    /* whole box right of the open range / left of it / beyond the far distance */
    if ((s32)bsp_rnx * (bsp_rnx > 0 ? xs0 : xs1) + (s32)bsp_rny * (bsp_rny > 0 ? ys0 : ys1) > 0) {{ return 0; }}
    if ((s32)bsp_lnx * (bsp_lnx > 0 ? xs1 : xs0) + (s32)bsp_lny * (bsp_lny > 0 ? ys1 : ys0) < 0) {{ return 0; }}
    if ((s32)angleCos16 * (angleCos16 > 0 ? xs0 : xs1) + (s32)angleSin16 * (angleSin16 > 0 ? ys0 : ys1) > ((s32)BSP_FAR << FIX16_FRAC_BITS)) {{ return 0; }}
    bsp_cell_x1 = bsp_open_x1; bsp_cell_x2 = bsp_open_x2;
    if (!exact) {{ return 1; }}
    s16 cmin = 32767, cmax = -32768;
    u8 front = 0;
    for (u8 k = 0; k < 4; k++) {{
        s16 tlx = (k & 1) ? xs1 : xs0;
        s16 tly = (k & 2) ? ys1 : ys0;
        s32 rx = ((tlx * angleSin16) - (tly * angleCos16)) >> FIX16_FRAC_BITS;
        s16 rz = ((tlx * angleCos16) + (tly * angleSin16)) >> FIX16_FRAC_BITS;
        s16 c;
        if (rz > 0) {{ front = 1; }}
        if (rz < 16) {{ c = rx < 0 ? -1000 : 1000; }}   /* beside/behind the eye: unbounded on that side */
        else {{
            if (rx > rz + rz) {{ rx = rz + rz; }}
            if (rx < -(rz + rz)) {{ rx = -(rz + rz); }}
            c = (RENDER_WIDTH/2) + divs_32_by_16(rx * (RENDER_WIDTH/2), rz);
        }}
        if (c < cmin) {{ cmin = c; }}
        if (c > cmax) {{ cmax = c; }}
    }}
    if (!front) {{ return 0; }}
    cmin -= 1; cmax += 2;
    if (cmin < (s16)bsp_cell_x1) {{ cmin = bsp_cell_x1; }}
    if (cmax > (s16)bsp_cell_x2) {{ cmax = bsp_cell_x2; }}
    if (cmin >= cmax) {{ return 0; }}
    if (!manifold_open_cols(cmin, cmax)) {{ return 0; }}
    bsp_cell_x1 = cmin; bsp_cell_x2 = cmax;
    return 1;
}}

static void bsp_walk(s16 child) {{
    for (;;) {{
        if (child < 0) {{
            s16 cell = -child - 2;
            if (cell >= 0) {{
                manifold_bsp_cells++;
                visit_graph(bsp_src, cell, bsp_cell_x1, bsp_cell_x2, bsp_frame, 0);
                bsp_refresh_open();
            }}
            return;
        }}
        const s16* n = &e1_bsp_nodes[child * 14];
        s32 cr = (s32)n[2] * (playerYInt - n[1]) - (s32)n[3] * (playerXInt - n[0]);
        u8 side = cr > 0 ? 1 : 0;
        s16 ch = n[12 + side];
        if (bsp_box_visible(n + 4 + side * 4, ch < 0)) {{ bsp_walk(ch); }}
        if (bsp_done) {{ return; }}
        side ^= 1;
        ch = n[12 + side];
        if (!bsp_box_visible(n + 4 + side * 4, ch < 0)) {{ return; }}
        child = ch;
    }}
}}

void manifold_bsp_render(u16 src_sector, u16 wmin, u16 wmax, u32 cur_frame) {{
    if (!(&e1m1_map && cur_portal_map == &e1m1_map && e1_bsp_nodes)) {{
        manifold_bsp_mode = 0;
        visit_graph(src_sector, src_sector, wmin, wmax, cur_frame, 0);
        return;
    }}
    manifold_bsp_mode = 1;
    bsp_wmin = wmin; bsp_wmax = wmax; bsp_src = src_sector; bsp_frame = cur_frame;
    manifold_bsp_cells = 0;
    bsp_done = 0;
    bsp_open_x1 = wmin; bsp_open_x2 = wmax;
    bsp_refresh_open();
    if (!bsp_done) {{ bsp_walk(e1_bsp_num_nodes - 1); }}
    manifold_fill_open(wmin, wmax);
}}
"""
    p.write_text(s)
    d=out/"src/draw.c"
    ds=d.read_text()
    ds+="""
u8 manifold_open_range(u16 a, u16 b, s16* lo, s16* hi) {
    u8* yp = &yclip[a<<1];
    while (a < b && yp[1] <= yp[0]) { a++; yp += 2; }
    if (a >= b) { return 0; }
    yp = &yclip[(b-1)<<1];
    while (yp[1] <= yp[0]) { b--; yp -= 2; }
    *lo = a; *hi = b - 1;
    return 1;
}
u8 manifold_open_cols(u16 a, u16 b) {
    u8* yp = &yclip[a<<1];
    for (; a < b; a++, yp += 2) { if (yp[1] > yp[0]) { return 1; } }
    return 0;
}
/* close every still-open span with the fog colour (darkest entry, index 1) */
volatile u16 manifold_filled_rows;
void manifold_fill_open(u16 a, u16 b) {
    u8* yp = &yclip[a<<1];
    u16 filled = 0;
    for (; a < b; a++, yp += 2) {
        u8 lo = yp[0], hi = yp[1];
        if (hi > lo) {
            u16* dst = (u16*)(bmp_buffer_write + buf_column_offset_table[a] + ((u16)lo << 1));
            u8 n = hi - lo;
            filled += n;
            while (n--) { *dst++ = 0x1111; }
            yp[0] = 0; yp[1] = 0;
        }
    }
    manifold_filled_rows = filled;
}
"""
    d.write_text(ds)
    print("BSP-ordered renderer installed, far =",far)

def m13_bsp_all_leaves_diagnostic(out):
    """M13 diagnostic only: visit all BSP leaves front-to-back.

    Bypass bbox, frustum and depth culling in bsp_box_visible(), while
    retaining BSP ordering and existing per-column yclip occlusion.
    A large FPS cost is expected. This is NOT an optimization or a final
    fix; it isolates false-negative bbox rejection from projection/texture
    errors. Fog fill remains unchanged.
    """
    p=out/"src/portal.c"
    s=p.read_text()
    old="""    bsp_cell_x1 = bsp_open_x1; bsp_cell_x2 = bsp_open_x2;
    if (xs0 <= 0 && xs1 >= 0 && ys0 <= 0 && ys1 >= 0) { return 1; }"""
    new="""    bsp_cell_x1 = bsp_open_x1; bsp_cell_x2 = bsp_open_x2;
    /* M13 diagnostic: no node/leaf may be discarded by BSP bounding
       box tests. All remain subject to their wall projection/yclip. */
    return 1;
    if (xs0 <= 0 && xs1 >= 0 && ys0 <= 0 && ys1 >= 0) { return 1; }"""
    if s.count(old)!=1:
        raise ValueError("M13 all-leaves diagnostic: BSP box entry moved")
    s=s.replace(old,new,1)
    p.write_text(s)
    print("M13 BSP all-leaves diagnostic: bbox culling disabled (slow)")

def m13_bsp_far_fog(out):
    """M13.3 diagnostic only: apply the far-portal fog rule in BSP mode too.

    visit_graph() skips the fog-close rule when manifold_bsp_mode is set, so a
    far portal wall never closes its columns and relies on the neighbour leaf
    to do so. Where that neighbour wall is absent or culled, the columns stay
    open and manifold_fill_open() paints them blue. This patch closes them with
    the fog colour, as the non-BSP renderer does. It changes far-wall look and
    is NOT a fix; it measures how many holes are far-portal holes.
    """
    p=out/"src/portal.c"
    s=p.read_text()
    old="if (!manifold_bsp_mode && is_portal && ceil_color != 0"
    if s.count(old)!=1:
        raise ValueError("M13.3 far-fog: fog condition moved")
    s=s.replace(old,"if (is_portal && ceil_color != 0",1)
    p.write_text(s)
    print("M13.3 BSP far-portal fog diagnostic enabled")

def m13_fill_span_diag(out):
    """M13.3 diagnostic only: record the span of the last unclosed column.

    Writes manifold_fill_last_lo / _hi (rows) and manifold_fill_last_col for
    the last column that manifold_fill_open() paints. Lets the harness tell a
    top gap (lo == 0: ceiling or sky not drawn) from a floor gap (hi == SCREEN_HEIGHT)
    or a mid gap (wall not covering the column). Does not change any pixel.
    """
    p=out/"src/draw.c"
    s=p.read_text()
    old="""        if (hi > lo) {
            u16* dst = (u16*)(bmp_buffer_write + buf_column_offset_table[a] + ((u16)lo << 1));"""
    new="""        if (hi > lo) {
            manifold_fill_last_lo = lo; manifold_fill_last_hi = hi; manifold_fill_last_col = a;
            u16* dst = (u16*)(bmp_buffer_write + buf_column_offset_table[a] + ((u16)lo << 1));"""
    if s.count(old)!=1:
        raise ValueError("M13.3 fill diag: fill loop moved")
    s=s.replace(old,new,1)
    s=s.replace("volatile u16 manifold_filled_rows;","volatile u16 manifold_filled_rows;\nvolatile u8 manifold_fill_last_lo, manifold_fill_last_hi, manifold_fill_last_col;",1)
    p.write_text(s)
    print("M13.3 fill-span diagnostic enabled")

def m13_cull_off(out):
    """M13.3 diagnostic only: disable one bbox rejection test in bsp_box_visible().

    MANIFOLD_BSP_CULL_OFF is a comma list of: rnx, lnx, far, front, empty, cols.
    Each name removes the 'return 0' of that test, so the cell is kept. Used to
    find which test rejects cells whose columns the all-leaves build closes.
    Not a fix: cell count rises when a test is off.
    """
    keys=[k for k in os.environ.get("MANIFOLD_BSP_CULL_OFF","").split(",") if k]
    if not keys: return
    marks={
      "rnx":"if ((s32)bsp_rnx * (bsp_rnx > 0 ? xs0 : xs1)",
      "lnx":"if ((s32)bsp_lnx * (bsp_lnx > 0 ? xs1 : xs0)",
      "far":"> ((s32)BSP_FAR << FIX16_FRAC_BITS)) { return 0; }",
      "front":"if (!front) { return 0; }",
      "empty":"if (cmin >= cmax) { return 0; }",
      "cols":"if (!manifold_open_cols(cmin, cmax)) { return 0; }",
    }
    p=out/"src/portal.c"
    s=p.read_text()
    for k in keys:
        if k not in marks: raise ValueError("unknown cull key "+k)
        lines=s.split("\n")
        hit=[i for i,l in enumerate(lines) if marks[k] in l]
        if len(hit)!=1: raise ValueError(f"M13.3 cull {k}: {len(hit)} matches")
        lines[hit[0]]=lines[hit[0]].replace("{ return 0; }","{ }",1)
        s="\n".join(lines)
    p.write_text(s)
    print("M13.3 bbox tests disabled:", keys)

def m13_proj_fix(out):
    """M13.3 candidate: widen the wall column projection past 16 bits.

    project_and_adjust_x() does 'lsl.w #5' on the 16-bit x before muls.w, so any
    |x| above 1023 wraps and that wall is drawn at a wrong column. The C version
    keeps x*32 in 32 bits and returns the same value for every in-range input.
    Opt-in with MANIFOLD_PROJ_FIX=1 until measured.
    """
    p=out/"src/math3d.c"
    s=p.read_text()
    a=s.index("s16 project_and_adjust_x(s16 x, s16 z_recip) {")
    b=s.index("    return x;\n}",a)+len("    return x;\n}")
    old=s[a:b]
    if "lsl.w #5" not in old:
        raise ValueError("M13.3 proj fix: asm block moved")
    new=("s16 project_and_adjust_x(s16 x, s16 z_recip) {\n"
         "    /* M13.3: 32-bit x*32; the asm lsl.w wrapped for |x| > 1023 */\n"
         "    return (s16)((((s32)x * 32) * (s32)z_recip) >> 16) + 32;\n}")
    s=s[:a]+new+s[b:]
    p.write_text(s)
    print("M13.3 projection widened to 32-bit")

def m13_clear_diag(out):
    """M13.3 diagnostic only: clear the write buffer to a marker every frame.

    The renderer never clears bmp_buffer_write during play (only wireframe and
    debug paths do), so a column span that no draw paints shows the buffer from
    two frames earlier. This patch paints the write buffer with marker index
    0xFFFF first, so any pixel no draw covers shows as that marker. Not a fix.
    """
    d=out/"src/draw.c"
    ds=d.read_text()
    colour=os.environ.get("MANIFOLD_CLEAR_VALUE","0xFFFF")
    ds+="""
/* M13.3 diagnostic: clear the write buffer before the BSP render (value via MANIFOLD_CLEAR_VALUE) */
void manifold_diag_clear(void) {
    for (u16 a = 0; a < RENDER_WIDTH; a++) {
        u16* dst = (u16*)(bmp_buffer_write + buf_column_offset_table[a]);
        for (u16 r = 0; r < SCREEN_HEIGHT; r++) { dst[r] = %s; }
    }
}
""" % colour
    d.write_text(ds)
    p=out/"src/portal.c"
    s2=p.read_text()
    anchor="void manifold_bsp_render(u16 src_sector, u16 wmin, u16 wmax, u32 cur_frame) {"
    if s2.count(anchor)!=2 and s2.count(anchor)!=1: raise ValueError("clear diag: anchor count %d"%s2.count(anchor))
    s2=s2.replace("    manifold_bsp_cells = 0;\n","    manifold_bsp_cells = 0;\n    manifold_diag_clear();\n",1)
    s2=s2.replace("void manifold_bsp_render(u16 src_sector, u16 wmin, u16 wmax, u32 cur_frame);","void manifold_bsp_render(u16 src_sector, u16 wmin, u16 wmax, u32 cur_frame);\nvoid manifold_diag_clear(void);",1)
    p.write_text(s2)
    print("M13.3 marker-clear diagnostic enabled")

def m13_fall_snap(out):
    """M13.3 candidate: floor following on steps and accelerating fall.

    game.c lowers the eye by a fixed FIX32(8) per frame toward the rest height
    of the current sector group. On a staircase the eye lags the floor, so the
    player seems to float along the diagonal while the eye falls at a constant
    slow rate. This patch snaps down any drop up to FIX32(24) (the Doom step
    height) and accelerates longer falls from FIX32(4) by FIX32(2) per frame to
    a FIX32(32) cap. Opt-in with MANIFOLD_FALL=1 until measured on the console.
    """
    p=out/"src/game.c"
    s=p.read_text()
    old="""    if(cur_player_pos.z > rest_player_pos) {
        cur_player_pos.z -= FIX32(8);
    } else if (cur_player_pos.z < rest_player_pos) {
        cur_player_pos.z = rest_player_pos;
    }"""
    if s.count(old)!=1:
        raise ValueError("M13.3 fall: vertical block moved")
    new="""    {
        /* M13.3: step-down snap up to Doom step height, then accelerating fall */
        static s32 fall_vel = 0;
        s32 drop = cur_player_pos.z - rest_player_pos;
        if (drop > 0) {
            if (drop <= FIX32(24)) {
                cur_player_pos.z = rest_player_pos;
                fall_vel = 0;
            } else {
                fall_vel = fall_vel < FIX32(4) ? FIX32(4) : fall_vel + FIX32(2);
                if (fall_vel > FIX32(32)) fall_vel = FIX32(32);
                cur_player_pos.z -= fall_vel;
                if (cur_player_pos.z < rest_player_pos) cur_player_pos.z = rest_player_pos;
            }
        } else {
            fall_vel = 0;
            if (drop < 0) cur_player_pos.z = rest_player_pos;
        }
    }"""
    if os.environ.get("MANIFOLD_FALL_FAST","0")=="1":
        # M14: quicker fall: starts at 12, +6 per frame, cap 96 (default 4/+2/32)
        new=new.replace("FIX32(4) ? FIX32(4) : fall_vel + FIX32(2)","FIX32(12) ? FIX32(12) : fall_vel + FIX32(6)").replace("fall_vel > FIX32(32)) fall_vel = FIX32(32)","fall_vel > FIX32(96)) fall_vel = FIX32(96)")
        assert "FIX32(96)" in new and "FIX32(12)" in new
    s=s.replace(old,new,1)
    p.write_text(s)
    print("M13.3 fall: step snap and accelerating fall enabled")

def m13_trace(out):
    """M13.3 diagnostic only: log every wall/floor/ceiling draw call per frame.

    Each draw function appends (fn id, a, b, c, d, e) to a RAM ring trc_buf,
    reset at the start of manifold_bsp_render(). The Lua harness reads it on
    frames whose residual span is known. Opt-in with MANIFOLD_TRACE=1. Not a fix.
    """
    d = out/"src/draw.c"; ds = d.read_text()
    helper = """
volatile u16 trc_count;
volatile s16 trc_buf[256*6];
void trc(u16 fn, s16 a, s16 b, s16 c, s16 d, s16 e) {
    if (trc_count < 256) {
        u16 i = trc_count * 6;
        trc_buf[i] = fn; trc_buf[i+1] = a; trc_buf[i+2] = b;
        trc_buf[i+3] = c; trc_buf[i+4] = d; trc_buf[i+5] = e;
        trc_count++;
    }
}
"""
    inc = [m.end() for m in re.finditer(r'^#include[^\n]*\n', ds, re.M)]
    at = inc[-1] if inc else 0
    ds = ds[:at] + "void trc(u16 fn, s16 a, s16 b, s16 c, s16 d, s16 e);\n" + ds[at:]
    ds += helper
    specs = [
      ("void draw_upper_step(", "trc(1,x1,x2,x1_ytop,x2_ytop,nx1_ytop);"),
      ("void draw_lower_step(", "trc(2,x1,x2,x1_ybot,x2_ybot,nx1_ybot);"),
      ("void draw_ceiling_update_clip(", "trc(3,x1,x2,x1_ytop,x2_ytop,0);"),
      ("void draw_floor_update_clip(", "trc(4,x1,x2,x1_ybot,x2_ybot,0);"),
      ("void draw_solid_color_wall(", "trc(5,x1,x2,x1_ytop,x1_ybot,x2_ytop);"),
      ("void draw_wall(", "trc(6,x1,x2,x1_ytop,x1_ybot,x2_ytop);"),
      ("void draw_top_pegged_wall(", "trc(7,x1,x2,x1_ytop,x1_ybot,x2_ytop);"),
      ("void draw_bot_pegged_wall(", "trc(8,x1,x2,x1_ytop,x1_ybot,x2_ytop);"),
      ("void manifold_fill_open(u16 a, u16 b) {", "trc(9,a,b,0,0,0);"),
    ]
    for sig, call in specs:
        i = ds.index(sig)
        if sig.endswith("{"):
            j = i + len(sig)
        else:
            j = ds.index("{\n", i) + 2
        ds = ds[:j] + "    " + call + "\n" + ds[j:]
    d.write_text(ds)
    pp = out/"src/portal.c"; ps = pp.read_text()
    a = "    manifold_bsp_cells = 0;\n"
    if ps.count(a) != 1: raise ValueError("trace: reset anchor")
    ps = ps.replace(a, a + "    trc_count = 0;\n", 1)
    ps = ps.replace("void manifold_bsp_render(u16 src_sector, u16 wmin, u16 wmax, u32 cur_frame);",
                    "void manifold_bsp_render(u16 src_sector, u16 wmin, u16 wmax, u32 cur_frame);\nextern volatile u16 trc_count;", 1)
    pp.write_text(ps)
    print("M13.3 draw trace enabled")

def m13_bsp_normal_precision(out):
    """M13.2 G-02: preserve full BSP frustum normal signs.

    Original s16 normals wrap after multiplying fix16 sine/cosine by a
    render-column offset. Shift 12 bits *after* wide multiplication, then
    keep scaled coefficients in s32; bounding-box dot products stay
    comfortably within signed 32-bit for E1M1 coordinates.
    """
    p=out/"src/portal.c"
    s=p.read_text()
    old="static s16 bsp_rnx, bsp_rny, bsp_lnx, bsp_lny;"
    if s.count(old)!=1:
        raise ValueError("BSP precision: expected normal declaration once")
    s=s.replace(old,"static s32 bsp_rnx, bsp_rny, bsp_lnx, bsp_lny;",1)
    updates=(
        ("bsp_rnx = (RENDER_WIDTH/2) * angleSin16 - hi * angleCos16;",
         "bsp_rnx = ((s32)(RENDER_WIDTH/2) * angleSin16 - (s32)hi * angleCos16) >> 12;"),
        ("bsp_rny = -(RENDER_WIDTH/2) * angleCos16 - hi * angleSin16;",
         "bsp_rny = (-(s32)(RENDER_WIDTH/2) * angleCos16 - (s32)hi * angleSin16) >> 12;"),
        ("bsp_lnx = (RENDER_WIDTH/2) * angleSin16 - lo * angleCos16;",
         "bsp_lnx = ((s32)(RENDER_WIDTH/2) * angleSin16 - (s32)lo * angleCos16) >> 12;"),
        ("bsp_lny = -(RENDER_WIDTH/2) * angleCos16 - lo * angleSin16;",
         "bsp_lny = (-(s32)(RENDER_WIDTH/2) * angleCos16 - (s32)lo * angleSin16) >> 12;"),
    )
    for old,new in updates:
        if s.count(old)!=1:
            raise ValueError("BSP precision: expected "+old)
        s=s.replace(old,new,1)
    p.write_text(s)
    print("M13 BSP precision: frustum normals now correctly scaled s32")

def stable_view(out):
    """MANIFOLD_STABLE_VIEW=1. Measured in MAME: standing still, the idle
    'breathing' bob changes ~1/3 of the 3D pixels every frame (15 distinct
    images) and the dithered textures shimmer; pushing against a wall keeps the
    run bob going (z +-10 units while x/y are fixed), hugely magnified at
    close range. Doom has no idle bob and bobs from real momentum: drop the
    idle bob and advance the run bob only when the player actually moved."""
    p=out/"src/game.c"
    s=p.read_text()
    a="    fix32 idle_bob_amt = bobs[idle_bob_idx] * FIX32(.2);\n"
    if s.count(a)!=2: raise ValueError("idle bob layout changed")
    s=s.replace(a,"    fix32 idle_bob_amt = 0;   /* no idle breathing */\n")
    a="""        idle_bob_idx = 27;
        wait_idle_bob_idx = 16;

        run_bob_idx++;
        if(run_bob_idx >= 28) {
            run_bob_idx = 0;
        }
"""
    b="""        idle_bob_idx = 27;
        wait_idle_bob_idx = 16;

        if (cur_player_pos.x != curx || cur_player_pos.y != cury) {
            run_bob_idx++;
            if(run_bob_idx >= 28) {
                run_bob_idx = 0;
            }
        } else {
            run_bob_idx = 27;   /* blocked by a wall: no bob */
        }
"""
    if s.count(a)!=1: raise ValueError("run bob layout changed")
    p.write_text(s.replace(a,b,1))
    print("stable view: idle bob off, run bob only on real movement")

def hole_diag(out):
    """Diagnostic only (MANIFOLD_EXTRA=hole_diag): zero the write buffer before
    each 3D frame, so any column span the renderer leaves undrawn stays colour 0
    and can be counted from the emulator (in a normal ROM it shows 2-frame-old
    content from the other buffer = flicker)."""
    p=out/"src/portal.c"
    s=p.read_text()
    old="void portal_rend(u16 src_sector, u32 cur_frame) {\n"
    if s.count(old)!=1: raise ValueError("portal_rend changed")
    s=s.replace(old,"extern u8* bmp_buffer_write;\nu16 manifold_open_rows(void);\nvolatile u16 manifold_holes;\nvolatile u32 manifold_hole_frames;\n"+old+"    memset(bmp_buffer_write, 0, 128*144);\n",1)
    s=s.replace("volatile u16 manifold_holes;\n","volatile u16 manifold_holes;\nvolatile u16 manifold_why[8];\nvolatile u16 manifold_why_last[8];\n",1)
    s=s.replace("    memset(bmp_buffer_write, 0, 128*144);\n","    memset(bmp_buffer_write, 0, 128*144);\n    for (u8 k = 0; k < 8; k++) manifold_why[k] = 0;\n",1)
    s=s.replace("volatile u32 manifold_dbg_maxdepth;\n","volatile u32 manifold_dbg_maxdepth;\nextern volatile u16 manifold_why[8];\n",1)
    reasons=[("{ manifold_dbg[7]++; return; }","{ manifold_dbg[7]++; manifold_why[0]++; return; }"),
             ("    if(depth >= MAX_DEPTH ) {    \n","    if(depth >= MAX_DEPTH ) {    \n        manifold_why[1]++;\n"),
             ("    if(sector_rendered_cache[sector] & 0b1) {","    if(sector_rendered_cache[sector] & 0b1) { manifold_why[2]++;"),
             ("    if(sector_rendered_cache[sector] >= 10) {\n","    if(sector_rendered_cache[sector] >= 10) {\n        manifold_why[3]++;\n"),
             ("    if(sector == src_sector && depth != 0) { return; }","    if(sector == src_sector && depth != 0) { manifold_why[4]++; return; }"),
             ("                }\n\n            }\n\n            continue;\n        }\n\n        //KLog(\"potentially on-screen\");","                }\n\n            } else { manifold_why[is_portal ? 5 : 6]++; }\n\n            continue;\n        }\n\n        //KLog(\"potentially on-screen\");")]
    for a,b in reasons:
        if s.count(a)!=1: raise ValueError(f"hole_diag anchor changed: {a!r} x{s.count(a)}")
        s=s.replace(a,b,1)
    old2="    #ifdef DEBUG_PORTAL_CLIP\n    KLog(\"Rendered.\");\n    #endif\n    return;\n"
    if s.count(old2)!=1: raise ValueError("portal_rend tail changed")
    s=s.replace(old2,"    manifold_holes = manifold_open_rows(); if (manifold_holes) { manifold_hole_frames++; }\n    for (u8 k = 0; k < 8; k++) manifold_why_last[k] = manifold_why[k];\n    return;\n",1)
    p.write_text(s)
    d=out/"src/draw.c"
    ds=d.read_text()
    ds+="""
u16 manifold_open_rows(void) {
    u16 n = 0;
    for (u16 x = 2; x < RENDER_WIDTH-2; x++) {
        u8 lo = yclip[x<<1], hi = yclip[(x<<1)+1];
        if (hi > lo) { n += hi - lo; }
    }
    return n;
}
"""
    d.write_text(ds)
    print("hole diagnostic: write buffer zeroed per frame")

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
    /* magnified wall (taller than the 512-entry scaler tables): every texel
       covers >= 8 rows -> fill texel runs; no per-row or per-run mul/div */
    s16 dy = uy1 - uy0;
    if (dy <= 0 || y1 <= y0) { return; }
    u32 rpt = (u32)(u16)dy << 10;                         /* rows per texel, 16.16 */
    u16 t = (u16)divs_32_by_16((s32)(u16)(y0 - uy0) << 6, dy);
    if (t > 63) { t = 63; }
    u32 b = (u32)((u16)(t + 1) * (u16)dy) << 10;          /* end row of texel t, 16.16 */
    register u16* dst = (u16*)(col_ptr + ((u16)y0 << 1));
    s16 y = y0;
    for (;;) {
        s16 end = uy0 + (s16)(b >> 16);
        if (end > y1 || t >= 63) { end = y1; }
        s16 n = end - y;
        if (n > 0) {
            register u16 w = tex_column[t];
            y = end;
            switch (n & 7) {
                do {
                    *dst++ = w;
                    case 7: *dst++ = w;
                    case 6: *dst++ = w;
                    case 5: *dst++ = w;
                    case 4: *dst++ = w;
                    case 3: *dst++ = w;
                    case 2: *dst++ = w;
                    case 1: *dst++ = w;
                    case 0: ;
                    n -= 8;
                } while (n >= 0);
            }
        }
        if (y >= y1) { break; }
        t++;
        b += rpt;
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

def m12_safe_sprite_raster(out):
    """Diagnostic M12-only portable RLE sprite rasterizer.

    Portable, low-cost version of the confirmed working C sprite path.
    Restores the portal clip buffer and replaces per-pixel divisions with
    fixed-point stepping plus a per-sprite vertical lookup table.
    """
    p=out/"src/draw.c"
    s=p.read_text()
    import re
    m=re.search(r"\bvoid\s+draw_rle_sprite\s*\(",s)
    if not m: raise ValueError("M12 draw_rle_sprite not found")
    opening=s.index("{",m.end())
    depth=1;end=opening+1
    while depth and end<len(s):
        if s[end]=="{": depth+=1
        elif s[end]=="}": depth-=1
        end+=1
    if depth: raise ValueError("M12 sprite function braces not balanced")
    replacement=r"""void draw_rle_sprite(s16 x1, s16 x2, s16 ytop, s16 ybot,
    u16 window_min, u16 window_max, clip_buf* clipping_buffer,
    const rle_sprite* obj, object_link obj_link, obj_type type, u16 sector) {
    if (!obj || obj->num_columns != 64 || x2<=x1 || ybot<=ytop) return;
    s16 xa=x1>(s16)window_min ? x1 : (s16)window_min;
    s16 xb=x2<(s16)window_max ? x2 : (s16)window_max;
    if (xa<0) xa=0;
    if (xb>RENDER_WIDTH) xb=RENDER_WIDTH;
    s16 ya=ytop<0 ? 0 : ytop;
    s16 yb=ybot>SCREEN_HEIGHT ? SCREEN_HEIGHT : ybot;
    if (xb<=xa || yb<=ya) return;

    /* Divisions only twice per sprite, NEVER per screen pixel. */
    u32 dx=(u16)(x2-x1),dy=(u16)(ybot-ytop);
    u32 xstep=((u32)64<<16)/dx, ystep=((u32)64<<16)/dy;
    u32 xphase=(u32)(xa-x1)*xstep;
    u32 yphase=(u32)(ya-ytop)*ystep;
    /* Precompute scaled source rows once per sprite instead of per column.
       SCREEN_HEIGHT is 144 in the current engine. */
    u8 source_rows[SCREEN_HEIGHT];
    for (s16 y=ya; y<yb; y++) {
        u16 sy=(u16)(yphase>>16);
        source_rows[y]=sy<64 ? sy : 63;
        yphase+=ystep;
    }
    /* Avoid repeatedly RLE-decoding the same source column when upscaled. */
    u8 pixels[64];
    s16 cached_src=-1;
    u8 hit_center=0;
    for (s16 x=xa; x<xb; x++,xphase+=xstep) {
        s16 sx=(s16)(xphase>>16);
        if (sx>63) sx=63;
        if (sx!=cached_src) {
            cached_src=sx;
            memset(pixels,0,sizeof(pixels));
            const column* col=&obj->columns[sx];
            u16 pos=0,texpos=0;
            if (col->num_spans && (!col->spans || !col->texels)) continue;
            for (u16 j=0;j<col->num_spans && j<64;j++) {
                u16 skip=col->spans[j*2],len=col->spans[j*2+1];
                if (skip>64 || len>64 || pos+skip+len>64) break;
                pos+=skip;
                for (u16 k=0;k<len;k++) pixels[pos+k]=col->texels[texpos+k];
                pos+=len;
                texpos+=len;
            }
        }
        s16 col_top=ya,col_bot=yb;
        /* Restore the portal visibility mask, so covered pixels do not
           need raster work and objects cannot draw through solid walls. */
        if (clipping_buffer) {
            u8 clip_top=clipping_buffer->y_clip_buffer[x*2];
            u8 clip_bot=clipping_buffer->y_clip_buffer[x*2+1];
            if (col_top<clip_top) col_top=clip_top;
            if (col_bot>clip_bot) col_bot=clip_bot;
        }
        if (col_bot<=col_top) continue;
        u8* dest=bmp_buffer_write+buf_column_offset_table[x];
        for (s16 y=col_top;y<col_bot;y++) {
            u8 pix=pixels[source_rows[y]];
            if (pix) {
                /* 2 duplicated packed 4bpp pixels per framebuffer byte.
                   One aligned 16-bit store paints both bytes of a column. */
                ((u16*)dest)[y]=(u16)(((u16)pix<<8)|pix);
            }
        }
        if (x>=(RENDER_WIDTH/2-2) && x<=(RENDER_WIDTH/2+2)) hit_center=1;
    }
    if (hit_center) {
        drawn_to_center_cols=type;
        sprite_on_center_col=obj_link;
        center_object_sector=sector;
    }
    flip();
}
"""
    p.write_text(s[:m.start()]+replacement+s[end:])
    print("M12 optimized C RLE sprite raster installed with portal y-clipping")

def m12_tune_doors(out):
    """Use the Manifold sector-group DOOR state machine, but give the
    player time to cross, and do not close a door while inside it.

    Opt-in to the playable E1M1 door ROM only. Geometry/portal arrays and
    collision processing are unchanged.
    """
    p=out/"src/sector_group.c"
    s=p.read_text()
    # Only patch run_door(), never run_lift() timers.
    door_start=s.index("void run_door(")
    door_end=s.index("void run_lift(",door_start)
    door_code=s[door_start:door_end]
    old="                params[SECTOR_GROUP_PARAM_TICKS_LEFT_IDX] = 30;"
    if door_code.count(old)!=2:
        raise ValueError("M12 expected two timers within run_door")
    door_code=door_code.replace(old,"                params[SECTOR_GROUP_PARAM_TICKS_LEFT_IDX] = 105;",2)
    s=s[:door_start]+door_code+s[door_end:]
    old="""            if(ticks_left == 0) {
                //play_sfx(SFX_CLOSE_DOOR_ID, 1);"""
    new="""            /* A player standing inside the door's own sector must not
               be crushed or trapped by automatic closing. */
            if(sector_group(cur_player_pos.cur_sector, cur_portal_map) == sect_group) {
                params[SECTOR_GROUP_PARAM_TICKS_LEFT_IDX] = 105;
                break;
            }
            if(ticks_left == 0) {
                //play_sfx(SFX_CLOSE_DOOR_ID, 1);"""
    if s.count(old)!=1:
        raise ValueError("M12 door OPEN state changed")
    p.write_text(s.replace(old,new,1))
    print("M12 door timer 105 ticks, player-safe auto-close")


def m14_start_menu(out, spawn_x, spawn_y, spawn_ang, spawn_cell):
    """M14: START in game opens the multi-map level-select menu (warm restart through reset vector 0)
    instead of pausing.  A magic + the map id are left in work RAM for the menu (it reads them before
    touching anything), which opens on the level list with the current map selected.
    Exact resume is not possible: the next map start-up clears all work RAM, and the menu needs VRAM/CRAM."""
    import os as _o
    mapid={"E1M1":0,"E1M2":1,"E1M3":2,"E1M4":3,"E1M5":4,"E1M6":5,"E1M7":6,"E1M8":7,"E1M9":8}[_o.environ.get("MANIFOLD_MAP","E1M1")]
    sb=out/"src/doom_statusbar.c"; t=sb.read_text()
    t+="""
/* M14 START menu */
u16 m14_map_id_var;
void m14_save_and_menu(void) {
    __asm volatile("move.w #0x2700,%%sr" ::: "memory");
    *(volatile u32 *)0xFF0010 = 0x4D454E55UL;
    *(volatile u32 *)0xFF0014 = 0x4C560000UL | m14_map_id_var;
    __asm volatile("move.l 0x0,%%sp\\n move.l 0x4,%%a0\\n jmp (%%a0)" ::: "memory");
    for (;;) ;
}
"""
    sb.write_text(t)
    g=out/"src/game.c"; t=g.read_text()
    old="    if (start_pressed && !prev_start_pressed) {\n        if(paused) {"
    assert t.count(old)==1,"handle_input start anchor changed"
    t=t.replace(old,"    if (start_pressed && !prev_start_pressed) {\n        { extern void m14_save_and_menu(void); m14_save_and_menu(); }\n        if(paused) {",1)
    g.write_text(t)
    lv=out/"src/level.c"; t=lv.read_text()
    old=f"    const int init_player_sector = {spawn_cell};"
    assert t.count(old)==1,"level.c init sector anchor"
    t=t.replace(old,f"    {{ extern u16 m14_map_id_var; m14_map_id_var = {mapid}; }}\n"+old,1)
    lv.write_text(t)

def m14_level_exit(out):
    """M14: botao B perto de um interruptor de saida (Doom special 11/51) termina a fase: deixa
    magic 'EXIT' + mapa/secreto na RAM e reinicia no menu, que mostra a tela entre fases e
    carrega o proximo mapa."""
    sb=out/"src/doom_statusbar.c"; t=sb.read_text()
    t+="""
/* M14 level exit */
#include "game.h"
extern const struct { u16 count; s16 line[4][4]; u8 secret[4]; } m14_exit_tbl;
int m14_exit_near(void) {
    s32 px = cur_player_pos.x >> FIX32_FRAC_BITS, py = cur_player_pos.y >> FIX32_FRAC_BITS;
    for (u16 i = 0; i < m14_exit_tbl.count; i++) {
        s32 ax = m14_exit_tbl.line[i][0], ay = m14_exit_tbl.line[i][1];
        s32 dx = m14_exit_tbl.line[i][2] - ax, dy = m14_exit_tbl.line[i][3] - ay;
        s32 den = dx*dx + dy*dy, num = (px-ax)*dx + (py-ay)*dy;
        s32 cx, cy;
        if (num <= 0 || den == 0) { cx = ax; cy = ay; }
        else if (num >= den) { cx = ax + dx; cy = ay + dy; }
        else { cx = ax + (dx*num)/den; cy = ay + (dy*num)/den; }
        s32 ex = px-cx, ey = py-cy;
        if (ex*ex + ey*ey < 60*60) return 1 + m14_exit_tbl.secret[i];
    }
    return 0;
}
void m14_do_exit(int kind) {
    __asm volatile("move.w #0x2700,%%sr" ::: "memory");
    *(volatile u32 *)0xFF0010 = 0x45584954UL;
    *(volatile u32 *)0xFF0014 = 0x4C560000UL | ((u32)(kind - 1) << 8) | m14_map_id_var;
    __asm volatile("move.l 0x0,%%sp\\n move.l 0x4,%%a0\\n jmp (%%a0)" ::: "memory");
    for (;;) ;
}
"""
    sb.write_text(t)
    g=out/"src/game.c"; t=g.read_text()
    old="        pressing = 2;\n        if(!check_trigger_switch(&cur_player_pos)) {"
    assert t.count(old)==1,"B handler anchor changed"
    t=t.replace(old,"        pressing = 2;\n        { extern int m14_exit_near(void); extern void m14_do_exit(int); extern void m14_world_use(void); int k = m14_exit_near(); if (k) m14_do_exit(k); else m14_world_use(); }\n        if(!check_trigger_switch(&cur_player_pos)) {",1)
    g.write_text(t)


_M14_FAMS=["zombieman","sergeant","imp","demon","spectre","baron"]
def _m14_ai_tables():
    """r068: per-family id tables for the six monsters (kind 1..6); returns (fam_map, tables_before_death_tick)."""
    def I(f,suf=""): return "M14_ID_"+f.upper()+(("_"+suf.upper()) if suf else "")
    ent=[]
    for k,f in enumerate(_M14_FAMS,1):
        sufs=["","W1","WB","WD","AIM","ATK","PAIN","BK0","BK1","SL","SR"] if k<=3 else ["","W1","AIM","ATK","PAIN","BK0","BK1","SL","SR"]
        ent+=[f"[{I(f,x)}]={k}" for x in sufs]
    fam="static const u8 m14_fam[128]={"+",".join(ent)+",};"
    def row(fn): return "{0,0,0,0}," if fn is None else "{"+",".join(fn)+"},"
    walk=["{0,0,0,0}"]
    for k,f in enumerate(_M14_FAMS,1):
        walk.append("{%s,%s,%s,%s}"%((I(f),I(f,"WB"),I(f,"W1"),I(f,"WD")) if k<=3 else (I(f),I(f,"W1"),I(f),I(f,"W1"))))
    t="static const u8 m14_walkid[7][4]={"+",".join(walk)+"};\n"
    t+="static const u8 m14_rotid[7][4]={{0,0,0,0},"+",".join("{%s,%s,%s,%s}"%(I(f,"BK0"),I(f,"BK1"),I(f,"SL"),I(f,"SR")) for f in _M14_FAMS)+"};\n"
    t+="static const u8 m14_aim_id[7]={0,"+",".join(I(f,"AIM") for f in _M14_FAMS)+"};\n"
    t+="static const u8 m14_painf_id[7]={0,"+",".join(I(f,"PAIN") for f in _M14_FAMS)+"};\n"
    t+="static const u8 m14_dseq[7][2]={{0,0},"+",".join("{%s,%s}"%(I(f,"DH"),I(f,"D0")) for f in _M14_FAMS)+"};\n"
    t2="static const u8 m14_base_id[7]={0,"+",".join(I(f) for f in _M14_FAMS)+"};\n"
    t2+="static const u8 m14_atk_id[7]={0,"+",".join(I(f,"ATK") for f in _M14_FAMS)+"};\n"
    t2+="static const u8 m14_dead_id[7]={0,"+",".join(I(f,"DEAD") for f in _M14_FAMS)+"};\n"
    t2+="static const u8 m14_hp[7]={0,20,30,60,150,150,255};      /* demon/spectre 150; baron 1000 does not fit a byte -> 255 */\n"
    t2+="static const u8 m14_ratio[7]={0,35,35,55,50,50,40};      /* % of the player's step */\n"
    t2+="static const u8 m14_painch[7]={0,200,170,200,180,180,50};  /* Doom painchance /256 */\n"
    return fam,t,t2

def m14_monsters(out, spawn_x, spawn_y, spawn_ang, spawn_cell):
    """M14: basic enemy AI on top of Manifold's object state machine.

    zombieman / sergeant / imp become active objects (health, wake on sight or
    on a shot, chase with the engine's cell collision, ranged hitscan or melee
    attack gated by being visibly drawn, attack-frame flash, corpse decoration).
    Player shots do 5/10/15 damage to the object under the crosshair.  Player
    death respawns at the level start with 100% health.
    """
    import re
    # ---- level.c: monster facing / ambush from the thing (z field carries it); object.ang keeps it
    lv=out/"src/level.c"; t=lv.read_text()
    k="""                    thg->type
                );"""
    assert t.count(k)==1
    t=t.replace(k,"""                    thg->type
                );
                { extern void m14_set_last_ang(u8 a); m14_set_last_ang((u8)thg->z); }""",1)
    lv.write_text(t)
    ob=out/"src/object.c"; t=ob.read_text()
    k="object_link alloc_object_in_sector(u8 activate_tick, int sector_num, fix32 x, fix32 y, s16 z, uint8_t object_type) {"
    assert t.count(k)==1
    t=t.replace(k,"static object_link m14_last_alloc = NULL_OBJ_LINK;\n"+k,1)
    k="    object_link res = new_object_link();\n"
    assert t.count(k)==1
    t=t.replace(k,k+"    m14_last_alloc = res;\n",1)
    ob.write_text(t)
    # ---- object.c: AI rate: sleeping monsters look every 4th frame, chasers think every other frame
    ob=out/"src/object.c"; t=ob.read_text()
    k="""                } else {
                    OBJ_LINK_DEREF(cur_object).activate_tick = 0;
                }"""
    assert t.count(k)==1
    t=t.replace(k,"""                } else {
                    OBJ_LINK_DEREF(cur_object).activate_tick = (object_state_machines[state_idx].action == &look_for_player) ? 3 : 1;
                }""",1)
    ob.write_text(t)
    # ---- collision.c: line of sight (Doom P_CheckSight equivalent): walk the cells along the
    # monster->player line, fail on a solid wall crossing or a closed sector (door shut)
    c=out/"src/collision.c"; t=c.read_text()
    t+="""
u8 m14_los(s16 ax, s16 ay, u16 as, s16 bx, s16 by) {
    portal_map* mp = (portal_map*)cur_portal_map;
    s16 cur = as;
    s32 dx = bx - ax, dy = by - ay;
    u16 len = (u16)fastLength(dx, dy);
    u16 n = len / 48 + 1;
    s16 px = ax, py = ay;
    for (u16 i = 1; i <= n; i++) {
        s16 nx = ax + (s16)(dx * i / n), ny = ay + (s16)(dy * i / n);
        const s16* sg = &e1_block_segs[e1_block_offsets[cur] * 5];
        u16 k = e1_block_offsets[cur + 1] - e1_block_offsets[cur];
        for (; k; k--, sg += 5) if (manifold_step_crosses(px, py, nx, ny, sg)) return 0;
        if (!within_sector(FIX32(nx), FIX32(ny), cur)) {
            s16 nc = manifold_locate2(FIX32(nx), FIX32(ny), cur);
            if (nc < 0) return 0;
            u16 g = sector_group(nc, mp);
            if (get_sector_group_ceil_height(g) <= get_sector_group_floor_height(g)) return 0;
            cur = nc;
        }
        px = nx; py = ny;
    }
    return 1;
}
"""
    if '#include "sector_group.h"' not in t: t='#include "sector_group.h"\n'+t
    c.write_text(t)
    # ---- object.h: per-object runtime fields
    h=out/"src/object.h"; t=h.read_text()
    old="    uint8_t activate_tick;\n};"
    assert t.count(old)==1,"object struct changed"
    h.write_text(t.replace(old,"    uint8_t activate_tick;\n    uint8_t seen;\n    u16 cool;\n};",1))
    # ---- draw.c: mark objects that actually paint pixels (line of sight)
    d=out/"src/draw.c"; t=d.read_text()
    a=t.index("void draw_rle_sprite(")
    anchor="        if (col_bot<=col_top) continue;\n        u8* dest=bmp_buffer_write+buf_column_offset_table[x];"
    b=t.index(anchor,a)
    t=t[:b]+"        if (col_bot<=col_top) continue;\n        if (type==OBJECT && obj_link!=NULL_OBJ_LINK) OBJ_LINK_DEREF(obj_link).seen=1;\n        u8* dest=bmp_buffer_write+buf_column_offset_table[x];"+t[b+len(anchor):]
    d.write_text(t)
    # ---- doom_statusbar.c: player damage
    sb=out/"src/doom_statusbar.c"; t=sb.read_text()
    t+="""
u8 m14_player_dead_flag;
s32 m14_spawn_x, m14_spawn_y; u16 m14_spawn_cell, m14_spawn_ang;
void m14_player_damage(u16 dmg) {
    if (dhud_state.armor > 0) {
        u16 a = dmg / 3;
        if (a > (u16)dhud_state.armor) a = dhud_state.armor;
        dhud_state.armor -= a; dmg -= a;
    }
    if (dmg >= (u16)dhud_state.health) {
        dhud_state.health = 100; dhud_state.armor = 0;
        dhud_state.ammo[0] = 50; dhud_state.ammo_r = 50;
        m14_player_dead_flag = 1;
    } else dhud_state.health -= dmg;
}
"""
    sb.write_text(t)
    # ---- object.c
    o=out/"src/object.c"; t=o.read_text()
    t=t.replace('#include <genesis.h>','#include <genesis.h>\n#include "m14_ids.h"\n#include "game.h"',1) if '#include <genesis.h>' in t else '#include <genesis.h>\n#include "m14_ids.h"\n#include "game.h"\n'+t
    for nm in ("look_for_player","follow_player"):
        old=f"int {nm}(object_link cur_obj, uint16_t cur_sector) {{"
        assert t.count(old)==1,nm
        t=t.replace(old,f"static int {nm}_orig(object_link cur_obj, uint16_t cur_sector) {{",1)
    old="    fix32 speed = FIX32(4.125); //obj_type->speed);"
    assert t.count(old)==1
    t=t.replace(old,"    fix32 speed = m14_speed_for(OBJ_LINK_DEREF(cur_obj).object_type);",1)
    # helpers go before dist_sqr (after the state machine table)
    helpers="""
extern u8 m14_player_dead_flag;
extern void m14_player_damage(u16 dmg);
static u8 m14_force_wake;
@@FAM@@
static u8 m14_kind(u8 t) { return t<128 ? m14_fam[t] : 0; }
extern u32 last_frame_ticks; extern void play_sfx(u8 id, u8 priority);
/* r057 animation: walk A,B,C,D (Doom run frames, 4 tics = 34/300 s each), pain, death sequence */
@@TABLES@@
/* attack: aim (E) -> fire frame (+damage) -> recover; units of 2/300 s (1 Doom tic ~ 4.3) */
static const u8 m14_at_T[7]={0,111,129,100,103,103,103};
static const u8 m14_at_aim[7]={0,43,43,34,34,34,34};
static const u8 m14_at_rec[7]={0,34,43,0,0,0,0};
static u8 m14_wf[64]; static u8 m14_wt[64]; static u8 m14_pt[64];   /* per-monster anim state; attack = wf bit7 + countdown in wt (no extra RAM) */
@@TABLES2@@
typedef struct { u8 link; u8 frame; u8 k; u16 sector; s16 left; } m14_death_t;
static m14_death_t m14dx[12]; static u8 m14dx_n;
void m14_death_tick(void) {
    s16 dt = last_frame_ticks > 300 ? 300 : last_frame_ticks;
    for (u8 i = 0; i < m14dx_n; ) {
        m14_death_t* e = &m14dx[i]; u8 done = 0;
        e->left -= dt;
        while (e->left <= 0 && !done) {
            e->left += 43; e->frame++;                                   /* Doom death frames: 5 tics each */
            if (e->frame >= 2) { DEC_LINK_DEREF(e->link).object_type = m14_dead_id[e->k]; done = 1; }
            else DEC_LINK_DEREF(e->link).object_type = m14_dseq[e->k][e->frame];
        }
        if (done) m14dx[i] = m14dx[--m14dx_n]; else i++;
    }
}
static fix32 m14_speed_for(u8 type) {
    u8 k=m14_kind(type);
    if (!k) return FIX32(4.125);
    u32 st=(move_speed*m14_ratio[k])/100;
    if (st<1) st=1;
    if (st>12) st=12;
    return FIX32(st*2);      /* chase runs every other frame (r056): double step */
}
"""
    _fam,_tab,_tab2=_m14_ai_tables()
    helpers=helpers.replace('@@FAM@@',_fam).replace('@@TABLES@@',_tab).replace('@@TABLES2@@',_tab2)
    anchor="fix32 dist_sqr(player_pos posa, player_pos origin) {"
    assert t.count(anchor)==1
    t=t.replace(anchor,helpers+anchor,1)
    old="    OBJ_LINK_DEREF(res).activate_tick = activate_tick;\n"
    assert t.count(old)==1
    t=t.replace(old,old+"    OBJ_LINK_DEREF(res).health = m14_hp[m14_kind(object_type)];\n    OBJ_LINK_DEREF(res).seen = 0;\n    OBJ_LINK_DEREF(res).cool = 0;\n",1)
    old="void wake_enemies_in_sector(u16 sector) {\n"
    assert t.count(old)==1
    t=t.replace(old,old+"    m14_force_wake = 1;\n",1)
    # reset force flag at the end of wake_enemies_in_sector: find its closing brace
    a=t.index(old); b=t.index("\n}\n",a)
    t=t[:b]+"\n    m14_force_wake = 0;"+t[b:]
    t+="""

static u16 m14_ticks(u16 hundredths) {      /* hundredths of a second -> 300 Hz ticks */
    return (u16)((u32)hundredths*3);
}
extern u16 random(void);
void m14_set_last_ang(u8 a) { if (m14_last_alloc != NULL_OBJ_LINK) OBJ_LINK_DEREF(m14_last_alloc).ang = a; m14_last_alloc = NULL_OBJ_LINK; }
/* facing a (0..127 = 0..360 deg, Doom: 0 = east, CCW, y up) vs direction to player */
static u8 m14_in_front(u8 a, s32 dx, s32 dy) {
    static const s8 c[16]={127,117,90,49,0,-49,-90,-117,-127,-117,-90,-49,0,49,90,117};
    u8 i = (u8)(((a + 4) >> 3) & 15);
    s8 cx = c[i], cy = c[(i + 12) & 15];          /* sin = cos shifted by 90 deg */
    return (s32)cx * dx + (s32)cy * dy > 0;
}
/* r068: which of the monster's views the player sees: 0 front, 1 back, 2 left side (A3), 3 right side (A7 mirrored) */
static u8 m14_view(u8 a, s32 dx, s32 dy, u32 d) {
    static const s8 c[16]={127,117,90,49,0,-49,-90,-117,-127,-117,-90,-49,0,49,90,117};
    u8 i = (u8)(((a + 4) >> 3) & 15);
    s32 cx = c[i], cy = c[(i + 12) & 15];
    s32 dot = cx * dx + cy * dy, lim = (s32)d * 63;      /* cos 60 deg */
    if (dot > lim) return 0;
    if (dot < -lim) return 1;
    return (cx * dy - cy * dx) > 0 ? 2 : 3;
}
/* direction of (dx,dy) as 0..127 = 0..360 deg (0 = +x, CCW); linear atan approximation per octant */
static u8 m14_bearing(s32 dx, s32 dy) {
    s32 ax = dx < 0 ? -dx : dx, ay = dy < 0 ? -dy : dy; u8 a;
    if (!ax && !ay) return 0;
    if (ay <= ax) a = (u8)((ay * 16) / ax); else a = (u8)(32 - (ax * 16) / ay);
    if (dx >= 0) return dy >= 0 ? a : (u8)((128 - a) & 127);
    return dy >= 0 ? (u8)(64 - a) : (u8)(64 + a);
}
static void m14_turn(object_link o, s32 dx, s32 dy, u8 maxstep) {      /* Doom monsters turn toward their goal in 45 deg steps */
    u8 b = m14_bearing(dx, dy), a = OBJ_LINK_DEREF(o).ang & 127, diff = (u8)((b - a) & 127);
    if (!diff) return;
    if (diff < 64) a = (u8)((a + (diff < maxstep ? diff : maxstep)) & 127);
    else { u8 n = (u8)(128 - diff); a = (u8)((a - (n < maxstep ? n : maxstep)) & 127); }
    OBJ_LINK_DEREF(o).ang = a;
}
int look_for_player(object_link cur_obj, uint16_t cur_sector) {
    u8 k=m14_kind(OBJ_LINK_DEREF(cur_obj).object_type);
    if (!k) return look_for_player_orig(cur_obj, cur_sector);
    int dx=F32_toInt(cur_player_pos.x-OBJ_LINK_DEREF(cur_obj).x);
    int dy=F32_toInt(cur_player_pos.y-OBJ_LINK_DEREF(cur_obj).y);
    u8 m14a=OBJ_LINK_DEREF(cur_obj).ang; u32 m14d=fastLength(dx,dy);
    /* Doom P_LookForPlayers: sight only in the monster's front 180 deg (unless within melee range 64);
       ambush (deaf) monsters ignore gunfire noise */
    u8 m14_front = m14_in_front(m14a&127, dx, dy) || m14d < 64;
    if ((m14_force_wake && !(m14a&128) && m14d<1600) || (OBJ_LINK_DEREF(cur_obj).seen && m14_front && m14d<2048)) {
        OBJ_LINK_DEREF(cur_obj).current_state=2;
        OBJ_LINK_DEREF(cur_obj).cool=m14_ticks(60);
        play_sfx(SFX_ENEMY_A_WAKE_ID, 8);
    }
    OBJ_LINK_DEREF(cur_obj).seen=0;
    { u8 v = m14_view(m14a & 127, dx, dy, m14d);                  /* idle: show the side/back the player is looking at */
      OBJ_LINK_DEREF(cur_obj).object_type = v ? m14_rotid[k][v == 1 ? 0 : v] : m14_base_id[k]; }
    return 1;
}

/* Doom hitscan: the monster aims at the player, then the angle gets a random spread of
   (P_Random()-P_Random())<<20 (triangular, max ~22.4 deg = 391 mrad).  The shot hits when the
   spread is within the player's angular half-width (radius 16 units -> 16000/d mrad). */
/* Doom P_CheckMissileRange (doom64kb src/p_enemy.c): dist-64, -128 more without a melee attack,
   capped at 200; attack unless P_Random() < dist. */
static u16 m14_missile_ok(u32 d) {
    s32 dd = (s32)d - 64 - 128; if (dd < 0) dd = 0; if (dd > 200) dd = 200;
    return (s32)(random() & 255) >= dd;
}
static u16 m14_aim_hit(u32 d) {
    if (d < 16) return 1;
    s32 a = 16000 / (s32)d; const s32 m = 391;
    if (a >= m) return 1;
    s32 sp = (s32)(random() & 255) - (s32)(random() & 255);      /* -255..255, triangular */
    sp = sp * m / 255; if (sp < 0) sp = -sp;
    return sp < a;
}
int follow_player(object_link cur_obj, uint16_t cur_sector) {
    u8 t=OBJ_LINK_DEREF(cur_obj).object_type;
    u8 k=m14_kind(t);
    if (!k) return follow_player_orig(cur_obj, cur_sector);
    int dx=F32_toInt(cur_player_pos.x-OBJ_LINK_DEREF(cur_obj).x);
    int dy=F32_toInt(cur_player_pos.y-OBJ_LINK_DEREF(cur_obj).y);
    u32 d=fastLength(dx,dy);
    { u8 L=cur_obj&63;                                        /* walk animation, pain, attack sequence */
      s16 dq=(2*(s16)last_frame_ticks+3)/4;
      if (m14_pt[L]) { s16 q=(s16)m14_pt[L]-dq; m14_pt[L]=(u8)(q>0?q:0); OBJ_LINK_DEREF(cur_obj).object_type=m14_painf_id[k]; return 1; }
      if (m14_wf[L]&0x80) {
          s16 q=(s16)m14_wt[L]-dq; if (q<0) q=0;
          u8 T=m14_at_T[k], fire_at=T-m14_at_aim[k];
          if ((u8)m14_wt[L]>fire_at && q<=fire_at) {          /* the shot leaves at the start of the fire frame */
              if (k==3) m14_player_damage(3*((random()&7)+1));
              else if (k==4 || k==5) m14_player_damage(4*((random()%10)+1));              /* bite */
              else if (k==6) { if (d<72) m14_player_damage(10*((random()&7)+1)); else if ((random()&255)<150) m14_player_damage(8*((random()&7)+1)); }   /* claw / fireball (instant, 60%) */
              else {
                  u8 pellets=(k==2)?3:1; u16 total=0;
                  for (u8 i=0;i<pellets;i++) { if (m14_aim_hit(d)) total+=3*((random()%5)+1); }
                  if (total) m14_player_damage(total);
                  play_sfx(SFX_SHOTGUN_ID, 5);
              }
          }
          m14_wt[L]=(u8)q; if (!q) { m14_wf[L]&=3; m14_wt[L]=17; }
          OBJ_LINK_DEREF(cur_obj).object_type = (q>fire_at || q<=m14_at_rec[k]) ? m14_aim_id[k] : m14_atk_id[k];
          return 1;
      }
      { s16 q=(s16)m14_wt[L]-dq; if (q<=0) { q=17; m14_wf[L]=(m14_wf[L]+1)&3; m14_turn(cur_obj, dx, dy, 16); } m14_wt[L]=(u8)q; }
      { u8 v = m14_view(OBJ_LINK_DEREF(cur_obj).ang & 127, dx, dy, d);
        OBJ_LINK_DEREF(cur_obj).object_type = v ? m14_rotid[k][v == 1 ? ((m14_wf[L] >> 1) & 1) : v] : m14_walkid[k][m14_wf[L]]; } }
    u8 seen=OBJ_LINK_DEREF(cur_obj).seen; extern u8 m14_los(s16 ax, s16 ay, u16 as, s16 bx, s16 by);
    OBJ_LINK_DEREF(cur_obj).seen=0;
    u16 cool=OBJ_LINK_DEREF(cur_obj).cool;
    cool = (cool>2*last_frame_ticks) ? (cool-2*last_frame_ticks) : 0;   /* every other frame */
    OBJ_LINK_DEREF(cur_obj).cool=cool;
    if (cool==0) {
        if ((k==3 || k==4 || k==5) || (k==6 && d<56)) {
            if (d<56) {                                      /* imp / demon / spectre / baron: melee */
                m14_turn(cur_obj, dx, dy, 128);
                m14_wf[cur_obj&63]|=0x80; m14_wt[cur_obj&63]=m14_at_T[k];
                OBJ_LINK_DEREF(cur_obj).object_type=m14_aim_id[k];
                OBJ_LINK_DEREF(cur_obj).cool=m14_ticks(k==3?90:70);
                return 1;
            }
        } else if (!m14_missile_ok(d)) {             /* Doom P_CheckMissileRange said no: re-check at the next chase decision */
            OBJ_LINK_DEREF(cur_obj).cool=m14_ticks(11*((random()&15)+1));   /* movecount 0..15 x 4 tics */
        } else if (seen || (d < 2048 && m14_los(F32_toInt(OBJ_LINK_DEREF(cur_obj).x), F32_toInt(OBJ_LINK_DEREF(cur_obj).y), cur_sector, F32_toInt(cur_player_pos.x), F32_toInt(cur_player_pos.y)))
                   || (OBJ_LINK_DEREF(cur_obj).cool = m14_ticks(11*((random()&15)+1)), 0)) {   /* sight test only at decision time (cheap path first) */
            m14_turn(cur_obj, dx, dy, 128);
            m14_wf[cur_obj&63]|=0x80; m14_wt[cur_obj&63]=m14_at_T[k];
            OBJ_LINK_DEREF(cur_obj).object_type=m14_aim_id[k];
            OBJ_LINK_DEREF(cur_obj).cool=m14_ticks(k==2?86:74);   /* attack states: 30 / 26 tics */
            return 1;
        }
    }
    if (d>40) follow_player_orig(cur_obj, cur_sector);
    return 1;
}

static u8 m14_dx_free(void) { return m14dx_n < 12; }
/* r073: Doom's tag-666 rule (E1M8): when no Baron of Hell is left alive, lower the tagged walls */
void m14_baron_check(void) {
    for (int s = 0; s < num_sector_lists; s++)
        for (object_link l = sector_object_lists[s]; l != NULL_OBJ_LINK; l = OBJ_LINK_DEREF(l).next)
            if (m14_kind(OBJ_LINK_DEREF(l).object_type) == 6) return;
    { extern void m14_fire_tag(s16 sp, s16 tag); m14_fire_tag(23, 666); }
}
void m14_hit_object(object_link o, u16 sector) {
    u8 k=m14_kind(OBJ_LINK_DEREF(o).object_type);
    if (!k) { free_object(o, sector); return; }
    extern u8 m14w_pellets(void); u16 dmg=0; for (u8 pi=0, pn=m14w_pellets(); pi<(pn==3?6:(pn?pn:1)); pi++) dmg+=5*((random()%3)+1);   /* every pellet of the current weapon hits (r069) */
    if (k==6) dmg=(dmg+3)>>2;   /* r073: Baron has 1000 hp in Doom but only 255 fit in the byte -> weapons do 1/4 damage to it */
    if (dmg>=OBJ_LINK_DEREF(o).health) {
        decoration_link dl = alloc_decoration_in_sector(sector, F32_toInt(OBJ_LINK_DEREF(o).x), F32_toInt(OBJ_LINK_DEREF(o).y),
                                   OBJ_LINK_DEREF(o).z, m14_dx_free() ? m14_dseq[k][0] : m14_dead_id[k]);
        if (dl != NULL_DEC_LINK && m14dx_n < 12) { m14_death_t* e=&m14dx[m14dx_n++]; e->link=dl; e->frame=0; e->k=k; e->sector=sector; e->left=43; }
        m14_wf[o&63]&=3; m14_pt[o&63]=0; play_sfx(77, 6);
        free_object(o, sector);
        if (k==6) m14_baron_check();
    } else {
        OBJ_LINK_DEREF(o).health-=dmg;
        OBJ_LINK_DEREF(o).current_state=2;
        if ((random()&255) < m14_painch[k]) { m14_pt[o&63]=7; m14_wf[o&63]&=3; play_sfx(76, 5); }   /* Doom painchance 200/256; pain state ~3 tics */
    }
}
"""
    o.write_text(t)
    # r071: (1) shots must pass through sprites that do not cover the crosshair row (corpses lying in front of a
    #       monster used to swallow the hit); (2) monsters used the wrong z unit for the step-height test (nukage pits blocked them)
    dc=out/"src/draw.c"; d=dc.read_text()
    o1="        if (x>=(RENDER_WIDTH/2-2) && x<=(RENDER_WIDTH/2+2)) hit_center=1;"
    assert d.count(o1)==1
    d=d.replace(o1,"        if (col_top<72+28 && col_bot>72-28) { if (x>=RENDER_WIDTH/2-2 && x<=RENDER_WIDTH/2+2) hit_center=2; else if (x>=RENDER_WIDTH/2-13 && x<=RENDER_WIDTH/2+13 && !hit_center) hit_center=1; }")   # r072: +-20% aim tolerance
    o3="    if (hit_center) {\n        drawn_to_center_cols=type;\n        sprite_on_center_col=obj_link;\n        center_object_sector=sector;\n    }"
    assert d.count(o3)==1
    d=d.replace(o3,"    if (hit_center && (hit_center==2 || (!m14_hx && (type==OBJECT || drawn_to_center_cols!=OBJECT)))) {\n        if (hit_center==2) m14_hx=1;\n        drawn_to_center_cols=type;\n        sprite_on_center_col=obj_link;\n        center_object_sector=sector;\n    }")
    o4="void reset_sprite_hit_info() {\n"
    assert d.count(o4)==1
    d=d.replace(o4,"static u8 m14_hx;\nvoid reset_sprite_hit_info() {\n    m14_hx = 0;\n")
    dc.write_text(d)
    t=o.read_text()
    o2="    s32 cur_obj_z = (cur_sector_height<<(FIX32_FRAC_BITS-4));"
    assert t.count(o2)==1
    o.write_text(t.replace(o2,"    s32 cur_obj_z = cur_sector_height;      /* same unit as the player's feet (floor<<4) */"))
    # ---- game.c: damage instead of instant kill, respawn on death
    g=out/"src/game.c"; t=g.read_text()
    old="free_object(sprite_on_center_col, center_object_sector);"
    assert t.count(old)==1
    t=t.replace(old,"m14_hit_object(sprite_on_center_col, center_object_sector);",1)
    anchor="    static int jumping = 0;"
    assert t.count(anchor)==1
    t=t.replace(anchor,f"""    {{
        extern u8 m14_player_dead_flag;
        if (m14_player_dead_flag) {{
            m14_player_dead_flag = 0;
            extern s32 m14_spawn_x, m14_spawn_y; extern u16 m14_spawn_cell, m14_spawn_ang;
            cur_player_pos.x = m14_spawn_x;
            cur_player_pos.y = m14_spawn_y;
            cur_player_pos.cur_sector = m14_spawn_cell;
            cur_player_pos.ang = m14_spawn_ang;
            cur_player_pos.z = FIX32(-10000);
        }}
    }}
"""+anchor,1)
    t=t.replace('#include <genesis.h>','#include <genesis.h>\nextern void m14_hit_object(u8 o, u16 sector);',1)
    # weapon cooldown by time, not by frame (game runs at 3-10 fps: 12 frames = seconds)
    old_a="    static int shooting = 0;"
    assert t.count(old_a)==1
    t=t.replace(old_a,old_a+"\n    static int m14_anim_at = 4;",1)
    old_b="        if(shooting == 4) { set_weapon_anim(SHOTGUN_RELOAD_ANIM, DMA_QUEUE); }"
    assert t.count(old_b)==1
    t=t.replace(old_b,"        if(shooting == m14_anim_at) { set_weapon_anim(SHOTGUN_RELOAD_ANIM, DMA_QUEUE); }",1)
    old_c="        shooting = 12;"
    assert t.count(old_c)==1
    t=t.replace(old_c,"        { s32 sl = 135 / (last_frame_ticks ? last_frame_ticks : 1); if (sl < 2) sl = 2; if (sl > 12) sl = 12; shooting = sl; m14_anim_at = (sl > 4) ? 4 : 1; }",1)
    g.write_text(t)
    print("M14 monsters: AI installed")


def m14_hazards(out):
    """Damaging floors (nukage 5/10, hell slime 20) at Doom's rate: every 32 tics (~274 of the
    300 Hz getTick units); the radiation suit (60 s) negates them.  Death uses m14_player_damage
    (health reset + respawn).  Per-sector damage table comes from the map (portal_map.m14_dmg)."""
    pm=out/"src/portal_map.h"; t=pm.read_text()
    a="    map_object* things;\n} portal_map;"
    assert t.count(a)==1
    pm.write_text(t.replace(a,"    map_object* things;\n    const u8* m14_dmg;\n    const s16* m14_trig;\n    const s16* m14_stag;\n    const s16* m14_tele;\n} portal_map;",1))
    sb=out/"src/doom_statusbar.c"; t=sb.read_text()
    t+="""
#include "portal_map.h"
#include "level.h"
#include "game.h"
extern u32 m14_suit_left;
extern u32 last_frame_ticks;
extern void m14_player_damage(u16 dmg);
void m14_hazards(void) {
    static u32 acc;
@@DBGB@@    u32 dt = last_frame_ticks; if (dt > 300) dt = 300;
    if (m14_suit_left > dt) m14_suit_left -= dt; else m14_suit_left = 0;
    acc += dt;
    if (acc < 274) return;
    acc = 0;
    if (!cur_portal_map->m14_dmg) return;
    u8 d = cur_portal_map->m14_dmg[sector_group(cur_player_pos.cur_sector, cur_portal_map)];
    if (!d) return;
    if (d == 255) {                       /* r073: Doom sector special 11 (E1M8 finale): 20 damage / 32 tics, ends the level at <=10 health, suit does not help */
        extern void m14_do_exit(int kind);
        if (dhud_state.health <= 30) m14_do_exit(1); else m14_player_damage(20);
        return;
    }
    if (m14_suit_left && !(d >= 20 && (random() & 255) < 5)) return;
    m14_player_damage(d);
}

/* ---- M14 radiation-suit tint: PAL1 (3D view) goes green while the suit is active ---- */
static u8 m14t_on;
static inline void m14t_vb(void){ for(;;){ SYS_disableInts(); if (*(volatile u16*)0xC00004 & 8) return; SYS_enableInts(); __asm__ volatile("nop\\n nop\\n nop\\n nop"); } }
void m14_tint_tick(void) {
    u8 want = m14_suit_left && (m14_suit_left > 1200 || ((m14_suit_left / 150) & 1));
    if (want == m14t_on) return;
    const u16* src = cur_portal_map->palette;
    if (!src) return;
    m14t_on = want;
    m14t_vb();
    for (u16 i = 0; i < 16; i++) {
        u16 c = src[i];
        if (want) {
            u16 r = (c >> 1) & 7, g = (c >> 5) & 7, b = (c >> 9) & 7;
            r = (r * 3) >> 3; b = (b * 3) >> 3;
            if (g) { g += (g >> 2) + 1; if (g > 7) g = 7; }
            c = (b << 9) | (g << 5) | (r << 1);
        }
        PAL_setColor(16 + i, c);
    }
    SYS_enableInts();
}

/* ---- M14 world: tagged remote actions ---- */
#include "sfx.h"
static u8 m14w_fired[64];
static s32 m14w_px, m14w_py; static u8 m14w_have;
static u8 m14w_cls(s16 sp) {
    switch (sp) {
    case 2: case 4: case 29: case 61: case 63: case 86: case 90: case 103: return 1;
    case 5: case 18: case 20: case 22: case 91: case 92: return 2;
    case 23: case 36: case 38: case 60: case 70: case 71: case 82: case 98: return 3;
    case 10: case 21: case 62: case 88: case 120: case 121: case 122: case 123: return 4;
    case 39: case 97: return 5;
    }
    return 0;
}
static u8 m14w_is_switch(s16 sp) {
    switch (sp) { case 18: case 20: case 21: case 23: case 29: case 61: case 62: case 63: case 70: case 71: case 103: return 1; }
    return 0;
}
static u8 m14w_once(s16 sp) {
    switch (sp) { case 2: case 4: case 5: case 18: case 20: case 21: case 22: case 23: case 29: case 36: case 38: case 39: case 103: return 1; }
    return 0;
}
static void m14w_fire(s16 sp, s16 tag) {
    u8 cls = m14w_cls(sp);
    if (!cls || !tag) return;
    if (cls == 5) {
        const s16* t = cur_portal_map->m14_tele;
        if (!t) return;
        for (s16 i = 0; i < t[0]; i++) {
            const s16* e = &t[1 + i * 5];
            if (e[0] != tag) continue;
            cur_player_pos.x = (s32)e[1] << FIX32_FRAC_BITS;
            cur_player_pos.y = (s32)e[2] << FIX32_FRAC_BITS;
            cur_player_pos.cur_sector = e[4];
            cur_player_pos.ang = e[3];
            cur_player_pos.z = FIX32(-10000);
            m14w_have = 0;
            return;
        }
        return;
    }
    const s16* st = cur_portal_map->m14_stag;
    if (!st) return;
    for (u16 g = 0; g < cur_portal_map->num_sector_groups; g++) {
        if (st[g] != tag) continue;
        u8 ty = GET_SECTOR_GROUP_TYPE(cur_portal_map->sector_group_types[g]);
        u16 s = get_sector_group_state(g);
        if (ty == DOOR && cls == 1 && s == CLOSED) { set_sector_group_state(g, GOING_UP); propagate_sfx_from_sect_group(SFX_OPEN_DOOR_ID, 8, g, cur_player_pos.cur_sector); }
        else if (ty == STAIRS && cls == 2 && s == STAIRS_LOWERED) { set_sector_group_state(g, STAIRS_MOVING); propagate_sfx_from_sect_group(SFX_OPEN_DOOR_ID, 8, g, cur_player_pos.cur_sector); }
        else if (ty == STAIRS && cls == 3 && (s == STAIRS_RAISED || s == STAIRS_MOVING)) { set_sector_group_state(g, 3); propagate_sfx_from_sect_group(SFX_OPEN_DOOR_ID, 8, g, cur_player_pos.cur_sector); }
        else if (ty == LOWERING_STAIRS && cls == 3 && s == STAIRS_LOWERED) { set_sector_group_state(g, STAIRS_MOVING); propagate_sfx_from_sect_group(SFX_OPEN_DOOR_ID, 8, g, cur_player_pos.cur_sector); }
        else if (ty == LIFT && cls == 4 && s == CLOSED) { set_sector_group_state(g, GOING_DOWN); }
    }
}
void m14_fire_tag(s16 sp, s16 tag) { m14w_fire(sp, tag); }
void m14_world_tick(void) {
    const s16* tr = cur_portal_map->m14_trig;
    s32 px = cur_player_pos.x >> FIX32_FRAC_BITS, py = cur_player_pos.y >> FIX32_FRAC_BITS;
    if (!m14w_have) { m14w_px = px; m14w_py = py; m14w_have = 1; return; }
    if (tr) {
        for (s16 i = 0; i < tr[0]; i++) {
            const s16* l = &tr[1 + i * 7];
            s16 sp = l[4];
            if (m14w_is_switch(sp) || (m14w_once(sp) && m14w_fired[l[6]])) continue;
            s32 ax = l[0], ay = l[1], dx = l[2] - ax, dy = l[3] - ay;
            s32 s0 = dx * (m14w_py - ay) - dy * (m14w_px - ax);
            s32 s1 = dx * (py - ay) - dy * (px - ax);
            u8 hit = (s0 < 0 && s1 >= 0) || (sp != 39 && sp != 97 && s0 >= 0 && s1 < 0);
            if (!hit) continue;
            s32 u = dx * (px - ax) + dy * (py - ay);
            if (u < 0 || u > dx * dx + dy * dy) continue;
            m14w_fired[l[6]] = 1;
            m14w_fire(sp, l[5]);
            if (!m14w_have) return;
        }
    }
    m14w_px = px; m14w_py = py;
}
static s32 m14w_isqrt(s32 v) { s32 r = 0; while ((r + 1) * (r + 1) <= v) r++; return r; }
void m14_world_use(void) {
    const s16* tr = cur_portal_map->m14_trig;
    if (!tr) return;
    s32 px = cur_player_pos.x >> FIX32_FRAC_BITS, py = cur_player_pos.y >> FIX32_FRAC_BITS;
    for (s16 i = 0; i < tr[0]; i++) {
        const s16* l = &tr[1 + i * 7];
        s16 sp = l[4];
        if (!m14w_is_switch(sp) || (m14w_once(sp) && m14w_fired[l[6]])) continue;
        s32 ax = l[0], ay = l[1], dx = l[2] - ax, dy = l[3] - ay;
        s32 dd = dx * dx + dy * dy; if (!dd) continue;
        s32 u = dx * (px - ax) + dy * (py - ay);
        s32 cr = dx * (py - ay) - dy * (px - ax); if (cr < 0) cr = -cr;
        s32 len = m14w_isqrt(dd);
        if (u < -(len * 16) || u > dd + len * 16) continue;
        if (cr > 72 * len) continue;
        m14w_fired[l[6]] = 1;
        m14w_fire(sp, l[5]);
    }
}
"""
    t=t.replace("@@DBGB@@", "    { extern void m14_baron_check(void); m14_baron_check(); }\n" if os.environ.get("MANIFOLD_DBG_BARON")=="1" else "")
    sb.write_text(t)
    g=out/"src/game.c"; t=g.read_text()
    a="    m12_process_pickups();"
    assert t.count(a)==1
    t=t.replace(a,a+"\n    { extern void m14_hazards(void); extern void m14_world_tick(void); m14_hazards(); m14_world_tick(); }",1)
    g.write_text(t)
    # 255 decoration slots (links are u8; 0xFF = null)
    oh=out/"src/object.h"; t=oh.read_text()
    a="#define NULL_DEC_LINK 0b01111111"
    assert t.count(a)==1
    oh.write_text(t.replace(a,"#define NULL_DEC_LINK 0b11111111",1))
    o=out/"src/object.c"; t=o.read_text()
    t+="""
/* ---- M14 barrels: shoot -> explosion animation + radius damage + chain reaction ---- */
extern u32 last_frame_ticks;
extern void play_sfx(u8 id, u8 priority);
static u8 m14b_hp[128];
typedef struct { u8 link; u8 frame; u16 sector; s16 left; } m14_expl_t;
static m14_expl_t m14x[10];
static u8 m14x_n;
static void m14_dec_unlink(u8 link, u16 sector) {
    u8 prev = NULL_DEC_LINK, cur = sector_decoration_lists[sector];
    u16 guard = 0;
    while (cur != NULL_DEC_LINK && guard++ < MAX_DECORATIONS) {
        if (cur == link) {
            u8 nx = DEC_LINK_DEREF(cur).next;
            if (prev == NULL_DEC_LINK) sector_decoration_lists[sector] = nx; else DEC_LINK_DEREF(prev).next = nx;
            DEC_LINK_DEREF(cur).next = decoration_free_list; decoration_free_list = cur;
            return;
        }
        prev = cur; cur = DEC_LINK_DEREF(cur).next;
    }
}
static void m14_explode(u8 link, u16 sector, s16 delay);
static void m14_blast(u8 link, u16 sector) {
    s32 bx = DEC_LINK_DEREF(link).x, by = DEC_LINK_DEREF(link).y;
    s32 px = cur_player_pos.x >> FIX32_FRAC_BITS, py = cur_player_pos.y >> FIX32_FRAC_BITS;
    s32 dx = px - bx, dy = py - by; if (dx < 0) dx = -dx; if (dy < 0) dy = -dy;
    s32 d = (dx > dy ? dx : dy) - 16; if (d < 0) d = 0;
    if (d < 128) m14_player_damage((u16)(128 - d));
    for (u16 sct = 0; sct < num_sector_lists; sct++) {
        u8 l = sector_decoration_lists[sct]; u16 g = 0;
        while (l != NULL_DEC_LINK && g++ < MAX_DECORATIONS) {
            if (l != link && DEC_LINK_DEREF(l).object_type == M14_ID_BARREL) {
                s32 ex = DEC_LINK_DEREF(l).x - bx, ey = DEC_LINK_DEREF(l).y - by;
                if (ex < 0) ex = -ex; if (ey < 0) ey = -ey;
                if ((ex > ey ? ex : ey) < 108) m14_explode(l, sct, 60);
            }
            l = DEC_LINK_DEREF(l).next;
        }
    }
}
static void m14_explode(u8 link, u16 sector, s16 delay) {
    if (DEC_LINK_DEREF(link).object_type != M14_ID_BARREL) return;
    for (u8 i = 0; i < m14x_n; i++) if (m14x[i].link == link) return;
    if (m14x_n >= 10) { m14_dec_unlink(link, sector); return; }
    m14_expl_t* e = &m14x[m14x_n++];
    e->link = link; e->sector = sector; e->frame = delay ? 255 : 0; e->left = delay ? delay : 45;
    if (!delay) { DEC_LINK_DEREF(link).object_type = M14_ID_BEXP0; play_sfx(SFX_SHOTGUN_ID, 15); m14_blast(link, sector); }
}
void m14_shoot_dec(u8 link, u16 sector) {
    if (DEC_LINK_DEREF(link).object_type != M14_ID_BARREL) return;
    u8 n = link >> 1, sh = (link & 1) << 2;
    u8 cur = ((m14b_hp[n] >> sh) & 15) + (random() % 3) + 1;
    if (cur >= 4) { m14b_hp[n] &= ~(15 << sh); m14_explode(link, sector, 0); }
    else m14b_hp[n] = (m14b_hp[n] & ~(15 << sh)) | (cur << sh);
}
void m14_expl_tick(void) {
    s16 dt = last_frame_ticks > 300 ? 300 : last_frame_ticks;
    for (u8 i = 0; i < m14x_n; ) {
        m14_expl_t* e = &m14x[i];
        e->left -= dt;
        u8 done = 0;
        if (e->frame == 255) {
            if (e->left <= 0) {
                e->frame = 0; e->left = 45;
                DEC_LINK_DEREF(e->link).object_type = M14_ID_BEXP0; play_sfx(SFX_SHOTGUN_ID, 15); m14_blast(e->link, e->sector);
            }
        } else {
            while (e->left <= 0 && !done) {
                e->frame++; e->left += 45;
                if (e->frame >= 5) done = 1; else DEC_LINK_DEREF(e->link).object_type = M14_ID_BEXP0 + e->frame;
            }
        }
        if (done) {
            m14_dec_unlink(e->link, e->sector);
            m14x[i] = m14x[--m14x_n];
        } else i++;
    }
}
"""
    t=t.replace("#include <genesis.h>","#include <genesis.h>\n#include \"sfx.h\"\n#include \"game.h\"",1) if "sfx.h" not in t else t
    o.write_text(t)
    g=out/"src/game.c"; t=g.read_text()
    a="        if(drawn_to_center_cols == OBJECT && sprite_on_center_col != NULL_OBJ_LINK) {"
    assert t.count(a)==1
    t=t.replace(a,"        if (drawn_to_center_cols == DECORATION) { extern void m14_shoot_dec(u8 l, u16 s); m14_shoot_dec(sprite_on_center_col, center_object_sector); }\n"+a,1)
    a="m14_hazards(); m14_world_tick(); }"
    assert t.count(a)==1
    t=t.replace(a,"m14_hazards(); m14_world_tick(); { extern void m14_tint_tick(void); extern void m14_expl_tick(void); m14_tint_tick(); m14_expl_tick(); { extern void m14_death_tick(void); m14_death_tick(); } } }",1)
    g.write_text(t)
    print("M14 hazards: damaging floors + radiation suit, 255 decorations")


def m14_tex_span(out, span):
    """M14: perspective-correct texture coords only every `span` columns
    (default upstream: 4); linear in between. Fewer 32/16 divisions per wall."""
    import math
    lg=int(math.log2(span)); assert 1<<lg==span and span in (8,16)
    d=out/"src/draw.c"; t=d.read_text()
    a=t.index("void calculate_tex_coords_for_wall(")
    b=t.index("void calculate_tex_coords_for_wall_two_column(")
    f=t[a:b]
    def rep(old,new):
        nonlocal f
        assert f.count(old)==1,old
        f=f.replace(old,new)
    rep("cnt += 3;","cnt += %d;"%(span-1))
    rep("cnt>>=2;","cnt>>=%d;"%lg)
    rep("s16 d_one_over_z_16_times_4 = d_one_over_z_16 << 2;","s16 d_one_over_z_16_times_4 = d_one_over_z_16 << %d;"%lg)
    rep("s32 d_u_over_z_23_times_4 = d_u_over_z_23 << 2;","s32 d_u_over_z_23_times_4 = d_u_over_z_23 << %d;"%lg)
    rep("u_11_per_col >>= 2;","u_11_per_col >>= %d;"%lg)
    blk="move.w %1, %2\\t\\n\\\n            and.w %6, %2\\t\\n\\\n            move.w %3, (%0)+\\t\\n\\\n            move.w %2, (%0)+\\t\\n\\\n            add.w %4, %3\\t\\n\\\n            add.w %5, %1\\t\\n\\\n            \\t\\n\\\n            "
    i=f.index('        __asm volatile(\n            "\\t\\n\\\n')
    j=f.index('"\\\n        : "+a" (tex_col_ptr), "+r" (u_11_start)')
    head='        __asm volatile(\n            "\\t\\n\\\n            '
    f=f[:i]+head+blk*span+f[j:]
    t=t[:a]+f+t[b:]
    assert "u16 tex_col_buffer[RENDER_WIDTH*2+3];" in t
    t=t.replace("u16 tex_col_buffer[RENDER_WIDTH*2+3];","u16 tex_col_buffer[RENDER_WIDTH*2+48];")
    d.write_text(t)
def m14_no_sound(out):
    """M14 diagnostic: no music and no SFX (sfx_on/music_on start FALSE)."""
    for f,a,b in (("sfx.c","int sfx_on = TRUE;","int sfx_on = FALSE;"),("music.c","int music_on = TRUE;","int music_on = FALSE;")):
        p_=out/"src"/f; t=p_.read_text(); assert t.count(a)==1,f
        p_.write_text(t.replace(a,b))
def m14_view_trim(out, n):
    """M14: render only columns [n, RENDER_WIDTH-n) (each column = 4 px; n=2 -> one
    8x8 tile less on each side). Outer columns are never drawn (stay black)."""
    gh=out/"src/game.h"; t=gh.read_text()
    a="#define RENDER_WIDTH 64"; assert t.count(a)==1
    gh.write_text(t.replace(a,a+"\n#define M14_VL %d\n#define M14_VR (RENDER_WIDTH-%d)"%(n,n)))
    def edit(fn,pairs):
        f=out/"src"/fn; t=f.read_text()
        for old,new,cnt in pairs:
            assert t.count(old)==cnt,(fn,old,t.count(old))
            t=t.replace(old,new)
        f.write_text(t)
    edit("portal.c",[
      ("    if (x2 > RENDER_WIDTH) x2 = RENDER_WIDTH;\n    if (x1 >= x2) return;",
       "    if (x2 > M14_VR) x2 = M14_VR;\n    if (x1 < M14_VL) x1 = M14_VL;\n    if (x1 >= x2) return;",1),
      ("clipped & LEFT_FRUSTUM_CLIPPED ? 0 : project","clipped & LEFT_FRUSTUM_CLIPPED ? M14_VL : project",1),
      ("LEFT_FRUSTUM_CLIPPED) ? 0 : project_and_adjust_x","LEFT_FRUSTUM_CLIPPED) ? M14_VL : project_and_adjust_x",2),
      ("RIGHT_FRUSTUM_CLIPPED) ? RENDER_WIDTH : project_and_adjust_x","RIGHT_FRUSTUM_CLIPPED) ? M14_VR : project_and_adjust_x",2),
    ])
    f=out/"src/bunch_render.c"; t=f.read_text()
    assert t.count("s16 window_min = 0;\n    s16 window_max = RENDER_WIDTH;")>=1
    t=t.replace("s16 window_min = 0;\n    s16 window_max = RENDER_WIDTH;","s16 window_min = M14_VL;\n    s16 window_max = M14_VR;")
    t=t.replace("0, RENDER_WIDTH,","M14_VL, M14_VR,")
    f.write_text(t)
    edit("my_bmp.c",[('		bmp_buffer_1 = man_malloc(BMP_PITCH * BMP_VERTICAL_HEIGHT * sizeof(u8), "vertical bmp_buffer_1");\n	}\n',
      '		bmp_buffer_1 = man_malloc(BMP_PITCH * BMP_VERTICAL_HEIGHT * sizeof(u8), "vertical bmp_buffer_1");\n	}\n	memset(bmp_buffer_0, 0, BMP_PITCH * BMP_VERTICAL_HEIGHT); memset(bmp_buffer_1, 0, BMP_PITCH * BMP_VERTICAL_HEIGHT);\n',1)])
    edit("draw.c",[("    if (xa<0) xa=0;\n    if (xb>RENDER_WIDTH) xb=RENDER_WIDTH;","    if (xa<M14_VL) xa=M14_VL;\n    if (xb>M14_VR) xb=M14_VR;",1)])
def m14_static_params(out):
    """M14: maps without doors/lifts never change their sector-group parameters, so keep
    them in ROM instead of a RAM copy (E1M6: 250 groups x 8 x 2 B = 4000 B of heap, which
    shrank the stack and cut portal recursion to nothing)."""
    f=out/"src/level.c"; t=f.read_text()
    a='    live_sector_group_parameters = man_malloc(num_bytes, "live sector group params table");\n    memcpy(live_sector_group_parameters, cur_portal_map->sector_group_params, num_bytes);'
    assert t.count(a)==1
    t=t.replace(a,"    (void)num_bytes;\n    live_sector_group_parameters = (s16*)cur_portal_map->sector_group_params;   /* ROM, read-only (static map) */")
    b='    man_free(live_sector_group_parameters, "live sector group params table");\n'
    assert t.count(b)==1
    t=t.replace(b,"")
    f.write_text(t)
    print("M14 static sector params: no RAM copy")

def m14_generic_doors(out):
    """M14 (MANIFOLD_DOORS=2): generic doors/lifts/lowering pillars for E1M2..E1M9.
    - B near a portal into a LOWERING_STAIRS sector (S1 'lower floor' pillar) starts it lowering;
    - lowering sectors keep their floor colour (the stairs colour hack is removed);
    - door timer 105 ticks + player-safe auto close (same as E1M1)."""
    m12_tune_doors(out)
    f=out/"src/level.c"; t=f.read_text()
    a="if(next_sect_group_type_low_bits != DOOR && next_sect_group_type_low_bits != LIFT) {"
    assert t.count(a)==1
    t=t.replace(a,"if(next_sect_group_type_low_bits != DOOR && next_sect_group_type_low_bits != LIFT && next_sect_group_type_low_bits != LOWERING_STAIRS) {")
    b="""        } else if (tgt_sect_group_type_low_bits == LIFT) {
            set_sector_group_state(tgt_sect_group, GOING_DOWN);
        }"""
    assert t.count(b)==1
    t=t.replace(b,"""        } else if (tgt_sect_group_type_low_bits == LIFT) {
            set_sector_group_state(tgt_sect_group, GOING_DOWN);
        } else if (tgt_sect_group_type_low_bits == LOWERING_STAIRS) {
            if (get_sector_group_state(tgt_sect_group) == STAIRS_LOWERED) set_sector_group_state(tgt_sect_group, STAIRS_MOVING);
        }""")
    f.write_text(t)
    f=out/"src/sector_group.c"; t=f.read_text()
    i=t.index("void run_lowering_stairs(")
    j=t.index("set_sector_group_floor_color_inner(params, 12);",i)
    t=t[:j]+"/* floor colour hack removed */"+t[j+len("set_sector_group_floor_color_inner(params, 12);"):]
    f.write_text(t)
    print("M14 generic doors: lowering pillars + keycards")

def m14_hint_rearm(out):
    """Piscar de barras pretas ao girar: o VInt zera a fase do H-Int mas nao rearma o
    contador do H-Int. Se um H-Int atrasa/se perde, o registrador fica com o valor de outra
    fase e o quadro inteiro desalinha (display ligado tarde / apagado cedo). Rearma o
    contador da fase 0 em todo VInt."""
    p=out/"src/my_bmp.c"
    s=p.read_text()
    old="void do_vint_flip() {\n    phase = 0;\n"
    if s.count(old)!=1: raise ValueError("do_vint_flip changed")
    s=s.replace(old,old+"    VDP_setHIntCounter(((screenHeight - BMP_VERTICAL_HEIGHT) >> 1) - 8);\n")
    p.write_text(s)
    print("H-Int counter rearmed in every VInt")

def m14_hint_probe(out):
    """Diagnostico: guarda em RAM a linha (VCounter) em que cada fase do H-Int vertical roda."""
    p=out/"src/my_bmp.c"
    s=p.read_text()
    a=s.index("HINTERRUPT_CALLBACK bmp_do_hblank_process_vertical() {")
    b=s.index("HINTERRUPT_CALLBACK bmp_do_hblank_process_horizontal() {")
    body=s[a:b]
    body=body.replace("    const u16 scrh = screenHeight;\n","    const u16 scrh = screenHeight;\n    hint_probe[3]++; hint_probe[4+(phase&3)] = GET_VCOUNTER;\n",1)
    s=s[:a]+"volatile u16 hint_probe[16];\n"+body+s[b:]
    k="void do_vint_flip() {"
    if s.count(k)==1:
        s=s.replace(k,"static void do_vint_flip_inner() {")
        s+="\nvoid do_vint_flip() { u16 t0=GET_VCOUNTER; do_vint_flip_inner(); hint_probe[0]=t0; hint_probe[1]=GET_VCOUNTER; }\n"
    k="void request_flip() {\n"
    if s.count(k)==1:
        s=s.replace(k,k+"    hint_probe[8]=DMA_getQueueSize(); hint_probe[9]=(u16)DMA_getQueueTransferSize();\n")
    p.write_text(s)
    print("H-Int probe installed")

def m14_hint_margin(out, n):
    """Margem de tolerancia no H-Int vertical: acende o display n linhas mais cedo no topo e
    apaga n linhas mais tarde embaixo, para absorver H-Int atrasado (barras pretas piscando)."""
    p=out/"src/my_bmp.c"
    s=p.read_text()
    a=s.index("HINTERRUPT_CALLBACK bmp_do_hblank_process_vertical() {")
    b=s.index("HINTERRUPT_CALLBACK bmp_do_hblank_process_horizontal() {")
    body=s[a:b]
    o1="const u16 vborder = (scrh - 177) >> 1; // was 177?"
    o2="VDP_setHIntCounter(((scrh - BMP_VERTICAL_HEIGHT) >> 1) - 8);"
    if body.count(o1)!=1 or body.count(o2)!=1: raise ValueError("vertical H-Int body changed")
    body=body.replace(o1,"const u16 vborder = ((scrh - 177) >> 1) - %d;"%n).replace(o2,"VDP_setHIntCounter(((scrh - BMP_VERTICAL_HEIGHT) >> 1) - %d);"%(8+n))
    p.write_text(s[:a]+body+s[b:])
    print("H-Int margin",n)

def m14_ablate(out):
    """Diagnostico: tira do loop do jogo trabalhos que entram na fila de DMA do VInt."""
    g=out/"src/game.c"; t=g.read_text()
    if os.environ.get("MANIFOLD_NO_CONSOLE","0")=="1" and os.environ.get("MANIFOLD_NO_TEXT","0")!="1":
        if t.count("    console_tick();")!=1: raise ValueError("console_tick call changed")
        t=t.replace("    console_tick();","    /* console_tick(); ablated */")
    if os.environ.get("MANIFOLD_NO_TEXT","0")=="1":
        for k,r in ((("    showStats();","    /* showStats ablated */"),) if os.environ.get("MANIFOLD_FPS_ONLY","0")!="1" else ())+(
                    ("    console_tick();","    /* console_tick ablated */"),
                    ('    console_push_message_high_priority("game initialized!", 17, 2);',"    /* console msg ablated */"),):
            if t.count(k)!=1: raise ValueError("call changed: "+k)
            t=t.replace(k,r)
        print("all on-screen text removed")
    ev=int(os.environ.get("MANIFOLD_CONSOLE_EVERY","0"))
    if os.environ.get("MANIFOLD_NO_TEXT","0")=="1": ev=0
    if ev>1 and os.environ.get("MANIFOLD_NO_CONSOLE","0")!="1" and os.environ.get("MANIFOLD_NO_TEXT","0")!="1":
        if t.count("    console_tick();")!=1: raise ValueError("console_tick call changed")
        t=t.replace("    console_tick();","    { static u8 ctk; if(!(ctk++ & %d)) console_tick(); }"%(ev-1))
    if os.environ.get("MANIFOLD_NO_GUNBOB","0")=="1":
        k="void set_gun_pos() {\n"
        if t.count(k)!=1: raise ValueError("set_gun_pos changed")
        t=t.replace(k,k+"    return;\n")
    g.write_text(t); print("ablation applied")

def m14_sky_dma(out):
    """Piscar de barras ao girar: o ceu era reescrito inteiro (288 entradas, CPU, ints off) a cada
    mudanca de ang>>4. A fila de DMA do SGDK fica sempre cheia neste motor (nunca esvazia), entao
    DMA_QUEUE descarta tudo. Agora: MANIFOLD_SKY_ROWS linhas por quadro, via CPU no vblank."""
    rows=int(os.environ.get("MANIFOLD_SKY_ROWS","3"))
    p=out/"src/manifold_sky.c"
    s=p.read_text()
    i=s.index("void manifold_sky_update(void) {")
    new="""static u16 sky_pend; static s16 sky_off;
void manifold_sky_update(void) {
    sky_repair_once();
    if (!sky_ready) return;
    s16 off = (s16)((cur_player_pos.ang >> 4) & 15);
    if (off != sky_last) { sky_last = off; sky_off = off; sky_pend = 0x1FF; }
    u16 left = %d;
    for (u16 r = 0; r < 9 && sky_pend && left; r++) {
        if (!(sky_pend & (1 << r))) continue;
        for (u16 c = 0; c < 32; c++)
            sky_row_buf[c] = TILE_ATTR_FULL(PAL1, 0, 0, 0, sky_index[sky_map[r][(c + sky_off) & 15]]);
        M14_VB_BEGIN(); VDP_setTileMapDataRect(BG_B, sky_row_buf, SKY_X0, 4 + r, 32, 1, 32, CPU); SKY_CLEAR_BORDERS(4 + r, 1); M14_VB_END();
        sky_pend &= ~(1 << r); left--;
    }
}
""" % rows
    p.write_text(s[:i]+new)
    print("sky map update: %d rows/frame" % rows)

def m14_sky_gate(out):
    """Ceu so e atualizado quando algum setor com teto de ceu (ceil_color==0) foi renderizado no
    quadro anterior. Fora disso manifold_sky_update retorna sem tocar no VDP (sem barras ao girar)."""
    p=out/"src/manifold_sky.c"; s=p.read_text()
    o="void manifold_sky_update(void) {\n    sky_repair_once();\n    if (!sky_ready) return;\n"
    if s.count(o)!=1: raise ValueError("manifold_sky_update changed")
    s=s.replace(o,"u8 manifold_sky_seen;\n"+o+"    if (!manifold_sky_seen) return;\n    manifold_sky_seen = 0;\n",1)
    p.write_text(s)
    q=out/"src/portal.c"; t=q.read_text()
    o="    u8 ceil_color = get_sector_group_ceil_color(sect_group);\n\n    u8 cur_sect_group_type"
    if t.count(o)!=1: raise ValueError("portal ceil_color changed")
    t=t.replace(o,"    u8 ceil_color = get_sector_group_ceil_color(sect_group);\n    if (ceil_color == 0) manifold_sky_seen = 1;\n\n    u8 cur_sect_group_type",1)
    t="extern unsigned char manifold_sky_seen;\n"+t
    q.write_text(t)
    print("sky gate on visible sky ceilings")

def m14_install_display_hint_variants(out):
    if os.environ.get("MANIFOLD_HINT_REARM","0")=="1": m14_hint_rearm(out)
    if os.environ.get("MANIFOLD_KEEP_DISPLAY","0")=="1": keep_display_enabled_in_hblank(out)
    if os.environ.get("MANIFOLD_HINT_PROBE","0")=="1": m14_hint_probe(out)
    m14_ablate(out)
    if os.environ.get("MANIFOLD_SKY_DMA","0")=="1": m14_sky_dma(out)
    if os.environ.get("MANIFOLD_SKY_GATE","0")=="1": m14_sky_gate(out)
    if int(os.environ.get("MANIFOLD_HINT_MARGIN","0")): m14_hint_margin(out,int(os.environ["MANIFOLD_HINT_MARGIN"]))


def m14_all_keys(out):
    """M14: the player always carries the blue, red and green(yellow) keys (tech demo: open every door)."""
    f=out/"src/inventory.c"; t=f.read_text()
    a="void inventory_reset() {\n    num_items = 0;\n"
    assert t.count(a)==1
    t=t.replace(a,"void inventory_reset() {\n    num_items = 0;\n    inventory[num_items++] = BLUE_KEY; inventory[num_items++] = RED_KEY; inventory[num_items++] = GREEN_KEY;\n")
    f.write_text(t)
    print("M14 all keys in inventory")

def m14_lat_clip(out):
    """M14 experiment (MANIFOLD_LAT_CLIP=1): geometric, 32-bit lateral frustum clipping of walls before projection.
    Clips each wall against the 45-degree side planes (z16+16x>=0, z16-16x>=0), keeps the texture u range consistent
    and forces the edge columns (LEFT/RIGHT_FRUSTUM_CLIPPED) so the last column is not left undrawn.
    Fixes E1M4 yard triangles (wall projected 13..431 instead of 13..63)."""
    f=out/"src/portal.c"; t=f.read_text()
    call="        clip_result clipped = clip_map_vertex_16((Vect2D_s16*)&trans_v1, (Vect2D_s16*)&trans_v2, &tmap_info);\n"
    assert t.count(call)==1
    patch='''        u8 lat_flags = 0;
        {
            s32 cx1 = trans_v1.x, cz1 = trans_v1.y, cx2 = trans_v2.x, cz2 = trans_v2.y;
            s32 tA = 0, tB = 65536;
            u8 lat_changed = 0;
            for (int pl = 0; pl < 2; pl++) {
                s32 sg = pl ? -16 : 16;
                s32 d1 = cz1 + sg * cx1, d2 = cz2 + sg * cx2;
                if (d1 < 0 && d2 >= 0) {
                    s32 tt = (s32)((((s32)(-d1)) << 16) / (d2 - d1));
                    cx1 += (s32)(((cx2 - cx1) * (tt >> 1)) >> 15);
                    cz1 += (s32)(((cz2 - cz1) * (tt >> 1)) >> 15);
                    tA += (s32)(((tB - tA) >> 1) * (tt >> 1) >> 14);
                    lat_changed = 1; if (pl == 0) lat_flags |= LEFT_FRUSTUM_CLIPPED;
                } else if (d2 < 0 && d1 >= 0) {
                    s32 tt = (s32)((((s32)d1) << 16) / (d1 - d2));
                    cx2 = cx1 + (s32)(((cx2 - cx1) * (tt >> 1)) >> 15);
                    cz2 = cz1 + (s32)(((cz2 - cz1) * (tt >> 1)) >> 15);
                    tB = tA + (s32)(((tB - tA) >> 1) * (tt >> 1) >> 14);
                    lat_changed = 1; if (pl == 1) lat_flags |= RIGHT_FRUSTUM_CLIPPED;
                }
            }
            if (lat_changed) {
                trans_v1.x = (s16)cx1; trans_v1.y = (s16)cz1; trans_v2.x = (s16)cx2; trans_v2.y = (s16)cz2;
                if (tmap_info.needs_texture) {
                    u32 sp = tmap_info.u_span;
                    tmap_info.u_base = (u16)(tmap_info.u_base + (u16)((sp * (u32)tA) >> 16));
                    tmap_info.u_span = (u16)((sp * (u32)(tB - tA)) >> 16);
                }
            }
        }
'''
    t=t.replace(call,patch+call+"        if (lat_flags && clipped != FRUSTUM_CULLED && clipped != NEAR_Z_CULLED) { clipped = (clip_result)(clipped | lat_flags); }\n")
    f.write_text(t)
    print("M14 lateral frustum clip (experiment)")

def m14_dyn_params(out):
    """M14: only sector groups that can move/flash (type != NO_TYPE: doors, lifts, lights,
    stairs) get a RAM copy of their 8 parameters; every other group is read straight from
    the ROM map.  Replaces the full per-map RAM copy (E1M6: 250 groups x 16 B = 4000 B of
    heap that starved visit_graph's stack).  slot table = 1 B per group, RAM = 16 B per
    dynamic group."""
    import re
    f=out/"src/sector_group.c"; t=f.read_text()
    anchor="s16* live_sector_group_parameters;\n"
    assert t.count(anchor)==1
    t=t.replace(anchor,anchor+"""u8* m14_dyn_slot;
s16* m14_dyn_ram;
static __attribute__((noinline)) s16* m14_gp(u16 g) {
    u8 s = m14_dyn_slot[g];
    if (s == 0xFF) return (s16*)cur_portal_map->sector_group_params + ((u32)g << NUM_SECTOR_GROUP_PARAMS_SHIFT);
    return m14_dyn_ram + ((u16)s << NUM_SECTOR_GROUP_PARAMS_SHIFT);
}
""",1)
    # &live[(X<<SHIFT)]  /  &live[X<<SHIFT]
    t,n1=re.subn(r"&live_sector_group_parameters\[\(?\s*([A-Za-z_][A-Za-z_0-9]*)\s*<<NUM_SECTOR_GROUP_PARAMS_SHIFT\s*\)?\]",r"m14_gp(\1)",t)
    # live[(X<<SHIFT)+IDX] / live[(X<<SHIFT) + IDX]
    t,n2=re.subn(r"live_sector_group_parameters\[\(\s*([A-Za-z_][A-Za-z_0-9]*)\s*<<NUM_SECTOR_GROUP_PARAMS_SHIFT\s*\)\s*\+\s*([A-Z_0-9]+)\]",r"m14_gp(\1)[\2]",t)
    left=t.count("live_sector_group_parameters[")
    assert left==0,("unconverted accessors",left)
    print("M14 dyn params: accessors patched",n1,n2)
    f.write_text(t)
    f=out/"src/level.c"; t=f.read_text()
    a='    live_sector_group_parameters = man_malloc(num_bytes, "live sector group params table");\n    memcpy(live_sector_group_parameters, cur_portal_map->sector_group_params, num_bytes);'
    assert t.count(a)==1
    t=t.replace(a,"""    (void)num_bytes;
    extern u8* m14_dyn_slot; extern s16* m14_dyn_ram;
    m14_dyn_slot = man_malloc(num_sector_groups + 1, "dyn group slot table");
    u16 nd = 0;
    for (u16 g = 0; g < num_sector_groups; g++) {
        if (GET_SECTOR_GROUP_TYPE(map->sector_group_types[g]) != NO_TYPE) m14_dyn_slot[g] = (u8)nd++;
        else m14_dyn_slot[g] = 0xFF;
    }
    m14_dyn_ram = man_malloc(nd * (NUM_SECTOR_GROUP_PARAMS * 2) + 2, "dyn group params");
    for (u16 g = 0; g < num_sector_groups; g++) {
        if (m14_dyn_slot[g] != 0xFF)
            memcpy(&m14_dyn_ram[(u16)m14_dyn_slot[g] << NUM_SECTOR_GROUP_PARAMS_SHIFT],
                   &map->sector_group_params[(u32)g << NUM_SECTOR_GROUP_PARAMS_SHIFT], NUM_SECTOR_GROUP_PARAMS * 2);
    }""")
    b='    man_free(live_sector_group_parameters, "live sector group params table");\n    live_sector_group_parameters = NULL;'
    assert t.count(b)==1
    t=t.replace(b,"""    { extern u8* m14_dyn_slot; extern s16* m14_dyn_ram;
      man_free(m14_dyn_ram, "dyn group params"); man_free(m14_dyn_slot, "dyn group slot table"); m14_dyn_ram = NULL; m14_dyn_slot = NULL; }""")
    f.write_text(t)
    print("M14 dyn params: level.c init/clean")

def m14_unpack_map(out):
    """M14 perf: portal_map is declared __packed__, so GCC reads each pointer
    field byte by byte (~30 instrs per u32). All its members are 2-byte aligned
    anyway on m68k, so dropping the attribute keeps the layout and lets the
    compiler use move.l."""
    f=out/"src/portal_map.h"; t=f.read_text()
    a="typedef struct __attribute__((__packed__)){\n    const u16 num_sector_groups;"
    assert t.count(a)==1
    f.write_text(t.replace(a,"typedef struct {\n    const u16 num_sector_groups;"))
    # same reasoning: structs whose members are all 2-byte aligned on m68k
    for fn,pat in (("obj_sprite.h",["typedef struct  __attribute__((__packed__))  {\n    const u16 num_spans;","typedef struct  __attribute__((__packed__)) {\n    // 2 bytes\n    const u16 num_columns;"]),
                   ("texture.h",["typedef struct __attribute__((__packed__)) {\n    const uint16_t* const dark;"])):
        f=out/"src"/fn; t=f.read_text()
        for a in pat:
            assert t.count(a)==1,(fn,a)
            t=t.replace(a,a.replace(" __attribute__((__packed__)) "," ",1).replace("  __attribute__((__packed__))  "," ",1))
        f.write_text(t)
def m14_max_depth(out, n):
    """M14 perf: stop the portal traversal after n portal hops."""
    f=out/"src/portal.c"; t=f.read_text()
    a="if (depth > 48 ||"
    assert t.count(a)==1
    f.write_text(t.replace(a,"if (depth > %d ||"%n))
def m14_max_revisits(out, n):
    """M14 perf: a sector may be entered at most n times per frame (upstream: 10)."""
    f=out/"src/portal.c"; t=f.read_text()
    a="if(sector_rendered_cache[sector] >= 10) {"
    assert t.count(a)==1
    f.write_text(t.replace(a,"if(sector_rendered_cache[sector] >= %d) {"%n))
def m14_skip_closed(out):
    """M14 perf, no visual loss: do not enter a sector when every screen column of
    its portal window is already fully covered (nothing more can be drawn there)."""
    d=out/"src/draw.c"; t=d.read_text()
    a="u8 is_column_drawn(u8 min_drawable_y, u8 max_drawable_y) {"
    assert t.count(a)==1
    t=t.replace(a,"""int m14_window_open(u16 x1, u16 x2) {
    const u8* p = &yclip[x1<<1];
    while (x1 < x2) {
        if (p[0] < p[1]) return 1;
        p += 2; x1++;
    }
    return 0;
}

"""+a)
    d.write_text(t)
    f=out/"src/portal.c"; t=f.read_text()
    a="    if (x1 >= x2) return;\n"
    assert t.count(a)>=1
    i=t.index("void visit_graph(")
    j=t.index(a,i)
    t=t[:j]+a+"    { extern int m14_window_open(u16,u16); if (depth != 0 && !m14_window_open(x1,x2)) return; }\n"+t[j+len(a):]
    f.write_text(t)
def m14_vg_micro(out):
    """M14 perf: small per-wall savings in visit_graph (no behaviour change)."""
    f=out/"src/portal.c"; t=f.read_text()
    i=t.index("void visit_graph(")
    j=t.index("\nvoid ",i+10) if "\nvoid " in t[i+10:] else len(t)
    body=t[i:j]
    def rep(old,new):
        nonlocal body
        assert body.count(old)==1,old
        body=body.replace(old,new)
    rep("manifold_dbg[1]++; manifold_dbg[clipped==UNCLIPPED?2:clipped==NEAR_Z_CULLED?3:clipped==FRUSTUM_CULLED?4:5]++;","if (clipped == FRUSTUM_CULLED) { continue; }")
    rep("    manifold_dbg[0]++;\n","")
    a=body.index("        texmap_params tmap_info = {")
    b=body.index("        };",a)+len("        };")
    body=body[:a]+"""        texmap_params tmap_info;
        tmap_info.repetitions = 1; tmap_info.u_base = 0; tmap_info.u_span = 0;
        tmap_info.needs_texture = !is_solid_color;
        if (!is_solid_color) {
            tmap_info.repetitions = (map->wall_tex_repetitions ? map->wall_tex_repetitions[portal_idx] : 1);
            tmap_info.u_base = (map->wall_tex_u ? map->wall_tex_u[(portal_idx)*2] : 0);
            tmap_info.u_span = (map->wall_tex_u ? (u16)(map->wall_tex_u[(portal_idx)*2+1]-map->wall_tex_u[(portal_idx)*2]) : 0);
        }"""+body[b:]
    t=t[:i]+body+t[j:]
    f.write_text(t)
def m14_input_fix(out):
    """M14: BUTTON_C in draw.c flip() is a leftover debug path (clears/copies
    framebuffers, waitMs(125)) that corrupts the BMP engine; disable it and
    let C fire as well as A."""
    d=out/"src/draw.c"; t=d.read_text()
    old="  if(JOY_readJoypad(JOY_1) & BUTTON_C) {"
    assert t.count(old)==1
    t=t.replace(old,"  if(0) {")
    d.write_text(t)
    g=out/"src/game.c"; t=g.read_text()
    assert t.count("joy_button_pressed(BUTTON_A)")==2
    t=t.replace("joy_button_pressed(BUTTON_A)","joy_button_pressed(BUTTON_A|BUTTON_C)")
    g.write_text(t)
    # SGDK XGM: sample ids 1..63 belong to the music, SFX must use >= 64
    h=out/"src/sfx.h"; t=h.read_text()
    import re
    t,nsub=re.subn(r"(#define SFX_\w+_ID )(\d+)",lambda m:m.group(1)+str(int(m.group(2))+63),t)
    assert nsub==8,nsub
    h.write_text(t)
    # recoil (works without tile uploads) + real shot sound
    t=g.read_text()
    a="    s16 bobOffY = gun_bobs[idx].y<<1;"
    assert t.count(a)==1
    t=t.replace(a,a+"\n    { extern s16 m14_recoil_y; bobOffY += m14_recoil_y; }")
    a="void set_gun_pos() {"
    assert t.count(a)==1
    t=t.replace(a,"s16 m14_recoil_y;\n"+a)
    a="        shooting--;\n"
    assert t.count(a)==1
    t=t.replace(a,a+"        m14_recoil_y = (shooting > 0) ? ((shooting > 3 ? 3 : shooting) * 6) : 0; set_gun_pos();\n")
    g.write_text(t)
    wad_snd=None
    try:
        import wad_textures as WT, struct as _st
        _w=WT.Wad(os.environ.get("MANIFOLD_WAD_SND","/home/claude/wad/d.wad"))
        _l=_w.lump(os.environ.get("MANIFOLD_SHOT_LUMP","DSPISTOL"))
        _rate=_st.unpack("<H",_l[2:4])[0]; _n=_st.unpack("<I",_l[4:8])[0]
        _pcm=list(_l[8+16:8+_n-16]) if _n>40 else list(_l[8:8+_n])
        _m=max(abs(x-128) for x in _pcm) or 1
        _nn=int(len(_pcm)*14000/_rate); _o=bytearray()
        for i in range(_nn):
            v=(_pcm[min(len(_pcm)-1,int(i*_rate/14000))]-128)*min(120/_m,2.0)
            _o.append(max(1,min(255,int(128+v))))
        wad_snd=(bytes(_o))
    except Exception as e:
        print("M14 WAD sound failed:",e)
    import wave,random,math
    random.seed(6)
    rate=14000; n=int(rate*0.32); lp=0.0; data=bytearray()
    for i in range(n):
        tt=i/rate
        env=math.exp(-tt*14.0)
        lp+= (random.uniform(-1,1)-lp)*(0.55 if tt<0.05 else 0.25)
        thump=math.sin(2*math.pi*(90-120*tt)*tt)*math.exp(-tt*18)
        v=(lp*0.9+thump*0.6)*env*1.6
        data.append(max(1,min(255,int(128+max(-1,min(1,v))*120))))
    wp=out/"res/sfx/shotgun.wav"
    with wave.open(str(wp),"wb") as w:
        w.setnchannels(1); w.setsampwidth(1); w.setframerate(rate); w.writeframes(wad_snd if wad_snd else bytes(data))
    b=out/"src/doom_statusbar.c"; t=b.read_text()
    old="(JOY_readJoypad(JOY_1) & BUTTON_A)"
    assert t.count(old)==1
    t=t.replace(old,"(JOY_readJoypad(JOY_1) & BUTTON_B)")
    b.write_text(t)
def m14_weapon_fix(out):
    """M14: make the weapon sprites actually show.

    Upstream waits for DMA_getQueueSize()==pre_queue_size before placing the
    hardware sprites; in this build the queue never drains to that exact size
    (cur_num_sprites stays 0, nothing is drawn), and the idle weapon is never
    placed at start-up.  Wait one game frame instead (the queue is flushed by
    the V-Int in between), place the idle sprites at start, and make the
    animation timers frame-rate aware.
    """
    w=out/"src/weapon_sprites.c"; t=w.read_text()
    assert t.count("if(DMA_getQueueSize() == pre_queue_size) {")==2
    t=t.replace("if(DMA_getQueueSize() == pre_queue_size) {","if(m14_wpn_ready()) {")
    anchor="void update_weapon_sprites(TransferMethod transfer_type);"
    assert t.count(anchor)==1
    t=t.replace(anchor,anchor+"""
extern u32 last_frame_ticks;
static u8 m14_wpn_wait;
static u32* m14_up_ptr; static u16 m14_up_left; static u16 m14_up_idx;
static void m14_up_chunk(TransferMethod tm) {          /* <=32 tiles (1 KB) per game frame */
    u16 n = (m14_up_left > 32) ? 32 : m14_up_left;
    if (!n) return;
    VDP_loadTileData(m14_up_ptr, m14_up_idx, n, tm);
    m14_up_ptr += n * 8; m14_up_idx += n; m14_up_left -= n;
}
static int m14_wpn_ready(void) {
    if (m14_up_left) { m14_up_chunk(DMA_QUEUE); return 0; }
    if (m14_wpn_wait) { m14_wpn_wait--; return 0; }
    return 1;
}""",1)
    t+="""
void m14_fire_anim(void) {
    if (M14_FLASH == 0) return;                                  /* diagnostic: no fire frame */
    if (transfer_pending != DONE || cur_anim_idx != 0) return;   /* one flash at a time */
    set_weapon_anim(2, DMA_QUEUE);                               /* tiles already resident: no upload */
    transfer_pending = DONE;
    update_weapon_sprites(DMA_QUEUE);
}
void m14_weapon_preload(void) {                                  /* fire frame -> tile buffer B, once */
    AnimationFrame* f = shotgun_reload.animations[0]->frames[0];
    VDP_loadTileSet(f->tileset, manifold_weapon_buf1, DMA);
}
"""
    old="        transfer_pending = TILES_LOADING;"
    assert t.count(old)==1
    t=t.replace(old,old+"\n        m14_wpn_wait = 1;",1)
    old="    if(cur_frame_timer-- <= 0 && transfer_pending == DONE) {"
    assert t.count(old)==1
    t=t.replace(old,"    if(transfer_pending == DONE && cur_frame_timer-- <= 0) {",1)
    old="    VDP_loadTileSet(frame->tileset, cur_upload_idx, transfer_type);"
    assert t.count(old)==1
    t=t.replace(old,"""    m14_up_ptr = frame->tileset->tiles; m14_up_left = m14_res ? 0 : frame->tileset->numTile; m14_up_idx = cur_upload_idx;
    if (transfer_type == DMA_QUEUE) m14_up_chunk(DMA_QUEUE);
    else while (m14_up_left) m14_up_chunk(transfer_type);""",1)
    old="    cur_frame_timer = entry.time;"
    assert t.count(old)==1
    t=t.replace(old,"    cur_frame_timer = entry.time;\n    if (entry.time > 0) { if (last_frame_ticks >= 60) cur_frame_timer = 0; else if (last_frame_ticks >= 30) cur_frame_timer = 1; }",1)
    # M14 weapon v2: idle (tile buffer A) and fire (buffer B) frames stay resident in
    # VRAM; firing only swaps the sprite tile index, with no DMA at the moment of the
    # shot (the old per-shot 64-tile upload arrived 2-3 game frames late and collided
    # with the PCM shot sound).
    old2="    cur_upload_idx = get_next_tile_loc_and_flip();"
    assert t.count(old2)==1
    t=t.replace(old2,"""    static u8 m14_inited; u8 m14_res = 0;
    if (anim_idx == 2) { cur_upload_idx = manifold_weapon_buf1; m14_res = 1; }
    else if (anim_idx == 0 && m14_inited) { cur_upload_idx = start_tile_loc; m14_res = 1; }
    else cur_upload_idx = get_next_tile_loc_and_flip();
    if (anim_idx == 0) m14_inited = 1;""",1)
    t="#define M14_FLASH "+("0" if os.environ.get("MANIFOLD_WEAPON_FLASH","1")=="0" else "1")+"\n"+t
    w.write_text(t)
    g=out/"src/game.c"; t=g.read_text()
    for call in ("set_weapon_anim(SHOTGUN_RELOAD_ANIM, DMA_QUEUE);",):
        if call in t:
            t=t.replace(call,"{ extern void m14_fire_anim(void); m14_fire_anim(); }")
    old="    set_weapon_anim(SHOTGUN_IDLE_ANIM, DMA);\n}"
    assert t.count(old)==1
    t=t.replace(old,"    set_weapon_anim(SHOTGUN_IDLE_ANIM, DMA);\n    { extern void update_weapon_sprites(TransferMethod t); update_weapon_sprites(DMA); }\n    { extern void m14_weapon_preload(void); m14_weapon_preload(); }\n}",1)
    o6="    XGM_setPCM(SFX_SHOTGUN_ID, sfx_shotgun, sizeof(sfx_shotgun));"
    assert t.count(o6)==1
    if os.environ.get("MANIFOLD_PCM_DELAY","1")=="1":
        t=t.replace(o6,"    XGM_setForceDelayDMA(TRUE);   /* M14: keep queued DMA from starving Z80 PCM (shot noise) */\n"+o6,1)
    g.write_text(t)
    print("M14 weapon fix: sprites placed at start, queue wait replaced")

def m14_tex_u(out):
    """MANIFOLD_TEX_U=1: per-wall texture U base/span from the emitter
    (Doom mapping, continuous across BSP fragments) instead of an integer
    repetition count that restarts the texture on every fragment.
    The clip code keeps producing left_u/right_u as 0..1 fractions of the
    wall; draw.c now maps them to base + fraction*span when span != 0."""
    h=out/"src/portal_map.h"
    s=h.read_text()
    old="    const u8* wall_tex_repetitions;\n"
    if s.count(old)!=1: raise ValueError("portal_map.h wall_tex_repetitions changed")
    h.write_text(s.replace(old,old+"    const u16* wall_tex_u;   /* M14: 8.8 U start,end per wall, in texture widths */\n",1))
    t=out/"src/texture.h"
    s=t.read_text()
    old="    u8 needs_texture;\n} texmap_params;"
    if s.count(old)!=1: raise ValueError("texmap_params layout changed")
    t.write_text(s.replace(old,"    u8 needs_texture;\n    u16 u_base;    /* M14: 8.8 texture widths */\n    u16 u_span;    /* M14: 8.8; 0 = legacy repetitions */\n} texmap_params;",1))
    d=out/"src/draw.c"
    s=d.read_text()
    old1="    u32 left_u_16 = (tmap_info->left_u * repetitions);\n    u32 right_u_16 = (tmap_info->right_u * repetitions);\n"
    if s.count(old1)!=2: raise ValueError("draw.c u sites changed: %d"%s.count(old1))
    new1="""    u32 left_u_16 = (tmap_info->left_u * repetitions);
    u32 right_u_16 = (tmap_info->right_u * repetitions);
    if (tmap_info->u_span) {
        u32 base = ((u32)tmap_info->u_base) << 8;
        left_u_16 = base + ((tmap_info->left_u * (u32)tmap_info->u_span) >> 8);
        right_u_16 = base + ((tmap_info->right_u * (u32)tmap_info->u_span) >> 8);
    }
"""
    s=s.replace(old1,new1)
    d.write_text(s)
    p=out/"src/portal.c"
    s=p.read_text()
    old="(map->wall_tex_repetitions ? map->wall_tex_repetitions[portal_idx] : 1),"
    if s.count(old)!=2: raise ValueError("portal.c repetitions sites changed: %d"%s.count(old))
    s=s.replace(old,old+" .u_base = (map->wall_tex_u ? map->wall_tex_u[(portal_idx)*2] : 0), .u_span = (map->wall_tex_u ? (u16)(map->wall_tex_u[(portal_idx)*2+1]-map->wall_tex_u[(portal_idx)*2]) : 0),")
    p.write_text(s)
    b=out/"src/bunch_render.c"
    s=b.read_text()
    old="            texmap_params tmap_info;\n"
    c=s.count(old)
    for idx in ("portal_idx","portal_index"):
        o2=f"                tmap_info.repetitions = cur_portal_map->wall_tex_repetitions[{idx}];\n"
        if s.count(o2)!=1: raise ValueError("bunch_render site changed: "+idx)
        s=s.replace(o2,o2+f"                tmap_info.u_base = cur_portal_map->wall_tex_u ? cur_portal_map->wall_tex_u[({idx})*2] : 0;\n                tmap_info.u_span = cur_portal_map->wall_tex_u ? (u16)(cur_portal_map->wall_tex_u[({idx})*2+1]-cur_portal_map->wall_tex_u[({idx})*2]) : 0;\n",1)
    b.write_text(s)
    print("M14 wall_tex_u installed (draw.c, portal.c x2, bunch_render x2)")

def m14_stairs_down(out):
    """r075: raised platforms (type STAIRS, e.g. E1M8 tag-2 platform) can go back down: state 3 lowers 32/tick
    to the base floor kept in scratch param 6 (set by emit_portal_map)."""
    f=out/"src/sector_group.c"; t=f.read_text()
    old="params[SECTOR_GROUP_PARAM_STATE_IDX] = STAIRS_RAISED;\n                }\n            } while(0);\n            break;\n"
    if t.count(old)!=1: raise ValueError("run_stairs changed: %d"%t.count(old))
    t=t.replace(old,old+"""        case 3: do {
                s16 base = params[SECTOR_GROUP_PARAM_SCRATCH_ONE_IDX];
                cur_height -= 32;
                params[SECTOR_GROUP_PARAM_FLOOR_HEIGHT_IDX] = cur_height;
                if(cur_height <= base) {
                    params[SECTOR_GROUP_PARAM_FLOOR_HEIGHT_IDX] = base;
                    params[SECTOR_GROUP_PARAM_STATE_IDX] = STAIRS_LOWERED;
                }
            } while(0);
            break;
""",1)
    f.write_text(t); print("r075 stairs can lower")

def m14_sprite_xform(out):
    """r076: sprites/decorations transform their position with an always_inline copy of transform_map_vert_16
    (no call/struct-return per object; the player sin/cos/pos globals are loaded once per sector loop)."""
    f=out/"src/portal.c"; t=f.read_text()
    anchor='#include "vertex.h"\n'
    if t.count(anchor)!=1: raise ValueError("portal.c include anchor changed")
    helper="""
static inline __attribute__((always_inline)) Vect2D_s16 m14_tv(s16 x, s16 y) {
    s16 tlx = x - playerXInt, tly = y - playerYInt;
    s32 rx = (tlx * angleSin16) - (tly * angleCos16);
    s32 ry = (tlx * angleCos16) + (tly * angleSin16);
    Vect2D_s16 v; v.x = rx >> FIX16_FRAC_BITS; v.y = ry >> (FIX16_FRAC_BITS - TRANS_Z_FRAC_BITS);
    return v;
}
"""
    t=t.replace(anchor,anchor+helper,1)
    for old in ("\n            Vect2D_s16 trans_pos = transform_map_vert_16(F32_toInt(obj_x), F32_toInt(obj_y));","\n            Vect2D_s16 trans_pos = transform_map_vert_16(obj_x, obj_y);"):
        n=t.count(old)
        if n!=1: raise ValueError("sprite transform site changed (%d): %s"%(n,old))
        t=t.replace(old,old.replace("transform_map_vert_16","m14_tv"))
    f.write_text(t); print("r076 sprite transform inlined")

def m14_perf(out):
    """r077 performance pass (same game logic, fewer cycles):
    1. collision.c manifold_radius_blocked: reject a wall segment by bounding box BEFORE the 4-cross-product swept test
       (it ran for every block segment of the sector on every step: 8 software 32x32 multiplies each).
    2. doom_statusbar.c m14_world_tick: skip when the player did not move and reject trigger lines by bbox (+ step slack)
       before the 4 software multiplies per line (it looped over every trigger line every frame).
    3. object.c monsters: one dot product shared by in_front/view, 16-bit muls (muls.w) and divu.w for the bearing."""
    def sub(f, old, new, what):
        t=f.read_text()
        if t.count(old)!=1: raise ValueError("m14_perf anchor changed (%d): %s"%(t.count(old),what))
        f.write_text(t.replace(old,new,1))
    c=out/"src/collision.c"
    sub(c,"""    for (; n; n--, s += 5) {
#if MANIFOLD_SWEPT
        if ((cx != nx || cy != ny) && manifold_step_crosses(cx, cy, nx, ny, s)) { return 1; }
#endif
        s16 lo = s[0] < s[2] ? s[0] : s[2], hi = s[0] < s[2] ? s[2] : s[0];
        if (nx < lo - MANIFOLD_R || nx > hi + MANIFOLD_R) { continue; }
        lo = s[1] < s[3] ? s[1] : s[3]; hi = s[1] < s[3] ? s[3] : s[1];
        if (ny < lo - MANIFOLD_R || ny > hi + MANIFOLD_R) { continue; }
""","""    u8 moving = (cx != nx || cy != ny);
    s16 sminx = cx < nx ? cx : nx, smaxx = cx < nx ? nx : cx;
    s16 sminy = cy < ny ? cy : ny, smaxy = cy < ny ? ny : cy;
    for (; n; n--, s += 5) {
        s16 xlo = s[0] < s[2] ? s[0] : s[2], xhi = s[0] < s[2] ? s[2] : s[0];
        s16 ylo = s[1] < s[3] ? s[1] : s[3], yhi = s[1] < s[3] ? s[3] : s[1];
#if MANIFOLD_SWEPT
        /* r077: a step can only cross a segment whose bounding box it overlaps */
        if (moving && !(smaxx < xlo || sminx > xhi || smaxy < ylo || sminy > yhi) && manifold_step_crosses(cx, cy, nx, ny, s)) { return 1; }
#endif
        if (nx < xlo - MANIFOLD_R || nx > xhi + MANIFOLD_R) { continue; }
        if (ny < ylo - MANIFOLD_R || ny > yhi + MANIFOLD_R) { continue; }
""","collision swept reorder")
    d=out/"src/doom_statusbar.c"
    sub(d,"""    if (!m14w_have) { m14w_px = px; m14w_py = py; m14w_have = 1; return; }
    if (tr) {
        for (s16 i = 0; i < tr[0]; i++) {
            const s16* l = &tr[1 + i * 7];
            s16 sp = l[4];
            if (m14w_is_switch(sp) || (m14w_once(sp) && m14w_fired[l[6]])) continue;
            s32 ax = l[0], ay = l[1], dx = l[2] - ax, dy = l[3] - ay;
""","""    if (!m14w_have) { m14w_px = px; m14w_py = py; m14w_have = 1; return; }
    s32 mvx = px - m14w_px, mvy = py - m14w_py; if (mvx < 0) mvx = -mvx; if (mvy < 0) mvy = -mvy;
    if (!mvx && !mvy) return;                 /* r077: did not move -> no line can be crossed */
    s32 mvm = mvx + mvy;
    if (tr) {
        for (s16 i = 0; i < tr[0]; i++) {
            const s16* l = &tr[1 + i * 7];
            s16 sp = l[4];
            if (m14w_is_switch(sp) || (m14w_once(sp) && m14w_fired[l[6]])) continue;
            {   /* r077: a hit needs the new position within |step| of the line segment (bbox reject before the multiplies) */
                s32 x0 = l[0], x1 = l[2], y0 = l[1], y1 = l[3];
                s32 lox = (x0 < x1 ? x0 : x1) - mvm, hix = (x0 < x1 ? x1 : x0) + mvm;
                s32 loy = (y0 < y1 ? y0 : y1) - mvm, hiy = (y0 < y1 ? y1 : y0) + mvm;
                if (px < lox || px > hix || py < loy || py > hiy) continue;
            }
            s32 ax = l[0], ay = l[1], dx = l[2] - ax, dy = l[3] - ay;
""","world_tick bbox")
    o=out/"src/object.c"
    sub(o,"""    s32 cx = c[i], cy = c[(i + 12) & 15];
    s32 dot = cx * dx + cy * dy, lim = (s32)d * 63;      /* cos 60 deg */
    if (dot > lim) return 0;
    if (dot < -lim) return 1;
    return (cx * dy - cy * dx) > 0 ? 2 : 3;
}""","""    s16 cx = c[i], cy = c[(i + 12) & 15];
    s16 sx = dx > 32767 ? 32767 : (dx < -32768 ? -32768 : dx), sy = dy > 32767 ? 32767 : (dy < -32768 ? -32768 : dy);
    s32 dot = (s32)cx * sx + (s32)cy * sy, lim = ((s32)d << 6) - (s32)d;      /* cos 60 deg; muls.w */
    if (dot > lim) return 0;
    if (dot < -lim) return 1;
    return ((s32)cx * sy - (s32)cy * sx) > 0 ? 2 : 3;
}
/* r077: same as m14_view, also reports "player in the front 180 deg" from the same dot product */
static u8 m14_view2(u8 a, s32 dx, s32 dy, u32 d, u8* front) {
    static const s8 c[16]={127,117,90,49,0,-49,-90,-117,-127,-117,-90,-49,0,49,90,117};
    u8 i = (u8)(((a + 4) >> 3) & 15);
    s16 cx = c[i], cy = c[(i + 12) & 15];
    s16 sx = dx > 32767 ? 32767 : (dx < -32768 ? -32768 : dx), sy = dy > 32767 ? 32767 : (dy < -32768 ? -32768 : dy);
    s32 dot = (s32)cx * sx + (s32)cy * sy, lim = ((s32)d << 6) - (s32)d;
    *front = dot > 0;
    if (dot > lim) return 0;
    if (dot < -lim) return 1;
    return ((s32)cx * sy - (s32)cy * sx) > 0 ? 2 : 3;
}
static inline u16 m14_divu16(u32 n, u16 dv) { __asm volatile("divu.w %1,%0" : "+d"(n) : "d"(dv)); return (u16)n; }""","monster view")
    sub(o,"""    if (ay <= ax) a = (u8)((ay * 16) / ax); else a = (u8)(32 - (ax * 16) / ay);""",
         """    if (ax > 32767) ax = 32767; if (ay > 32767) ay = 32767;
    if (ay <= ax) a = (u8)m14_divu16((u32)ay << 4, (u16)ax); else a = (u8)(32 - m14_divu16((u32)ax << 4, (u16)ay));   /* r077: divu.w, quotient <= 16 */""","bearing")
    sub(o,"u8 m14_front = m14_in_front(m14a&127, dx, dy) || m14d < 64;",
         "u8 m14_vf; u8 m14_v2 = m14_view2(m14a & 127, dx, dy, m14d, &m14_vf); u8 m14_front = m14_vf || m14d < 64;","look front")
    sub(o,"{ u8 v = m14_view(m14a & 127, dx, dy, m14d);","{ u8 v = m14_v2;","look view")
    if os.environ.get("MANIFOLD_PERF_SPRITE","1")!="1":
        print("r077 perf pass applied (sprite path off)"); return
    # 4. draw.c draw_rle_sprite: tall sprites draw per SOURCE row run (stores only), not per screen pixel with 2 table lookups
    dr=out/"src/draw.c"
    sub(dr,"""    u8 pixels[64];
    s16 cached_src=-1;
    u8 hit_center=0;""","""    u8 pixels[64];
    s16 cached_src=-1;
    u8 hit_center=0;
    /* r078: first screen row of each source row (source_rows is monotonic); used by the fast path for tall sprites */
    s16 fy[65]; u8 fast = (yb-ya) >= 56; u16 pmin=64, pmax=0;
    if (fast) {
        s16 yy=ya;
        for (u16 sy2=0; sy2<64; sy2++) { while (yy<yb && source_rows[yy]<sy2) yy++; fy[sy2]=yy; }
        fy[64]=yb;
    }""","rle sprite decls")
    sub(dr,"""            u16 pos=0,texpos=0;
            if (col->num_spans && (!col->spans || !col->texels)) continue;
            for (u16 j=0;j<col->num_spans && j<64;j++) {
                u16 skip=col->spans[j*2],len=col->spans[j*2+1];
                if (skip>64 || len>64 || pos+skip+len>64) break;
                pos+=skip;
                for (u16 k=0;k<len;k++) pixels[pos+k]=col->texels[texpos+k];
                pos+=len;
                texpos+=len;
            }""","""            u16 pos=0,texpos=0;
            pmin=64; pmax=0;
            if (col->num_spans && (!col->spans || !col->texels)) continue;
            for (u16 j=0;j<col->num_spans && j<64;j++) {
                u16 skip=col->spans[j*2],len=col->spans[j*2+1];
                if (skip>64 || len>64 || pos+skip+len>64) break;
                pos+=skip;
                if (len && pos<pmin) pmin=pos;
                for (u16 k=0;k<len;k++) pixels[pos+k]=col->texels[texpos+k];
                pos+=len;
                if (len) pmax=pos-1;
                texpos+=len;
            }""","rle sprite decode")
    sub(dr,"""        u8* dest=bmp_buffer_write+buf_column_offset_table[x];
        for (s16 y=col_top;y<col_bot;y++) {
            u8 pix=pixels[source_rows[y]];
            if (pix) {""","""        u8* dest=bmp_buffer_write+buf_column_offset_table[x];
        if (fast) {
            u16* dcol=(u16*)dest;
            for (u16 sy=pmin; sy<=pmax; sy++) {
                u8 pix=pixels[sy];
                if (!pix) continue;
                s16 y0=fy[sy], y1=fy[sy+1];
                if (y0>=col_bot) break;
                if (y1<=col_top) continue;
                if (y0<col_top) y0=col_top;
                if (y1>col_bot) y1=col_bot;
                if (y0>=y1) continue;
                u16 v=(u16)(((u16)pix<<8)|pix);
                u16* d=dcol+y0; u16* e=dcol+y1;
                while (d<e) *d++=v;
            }
        } else
        for (s16 y=col_top;y<col_bot;y++) {
            u8 pix=pixels[source_rows[y]];
            if (pix) {""","rle sprite draw")
    print("r077 perf pass applied")

def m14_fps_only(out):
    """r078: FPS counter only (no ROM-name tag, no console). Text plane write is skipped unless the
    shown value changed, and the value is sampled every 8 frames, so the per-frame cost is a counter test."""
    g=out/"src/game.c"; s=g.read_text()
    start=s.find("void showStats() {")
    if start<0: raise ValueError("showStats not found")
    end=s.find("\n}\n",start)
    if end<0: raise ValueError("showStats end not found")
    end+=3
    new="""
extern u32 last_frame_ticks;
static void manifold_fps_text(const char *t, u16 x, u16 y) {
    while (*t) { VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL3, 1, 0, 0, TILE_FONT_INDEX + (*t) - 32), x++, y); t++; }
}
void showStats() {
    static u8 sk; static u16 acc; static char last[8];
    acc += (u16)(last_frame_ticks > 600 ? 600 : last_frame_ticks);
    if (++sk & 15) return;
    /* real FPS = 16 frames / elapsed getTick() (300 ticks/s), one decimal */
    u32 f10 = acc ? (u32)48000UL / acc : 0; acc = 0;
    char num[8];
    num[0] = (char)('0' + (f10 / 100) % 10); u8 i = (f10 >= 100) ? 1 : 0;
    if (!i) { num[0] = (char)('0' + (f10 / 10) % 10); i = 1; }
    else { num[1] = (char)('0' + (f10 / 10) % 10); i = 2; }
    num[i++] = '.'; num[i++] = (char)('0' + f10 % 10); num[i] = 0;
    if (!strcmp(num, last)) return;
    strcpy(last, num);
    VDP_clearTileMapRect(BG_B, 0, 26, 12, 1);
    manifold_fps_text("FPS ", 1, 26);
    manifold_fps_text(num, 5, 26);
}
"""
    g.write_text(s[:start]+new+s[end:])
    print("r078 FPS-only counter")

def m14_door_header(out):
    """r073: a door's textured upper step is anchored at the door's open height. When the room ceiling is
    higher than that (E1M7 spawn: ceiling 128, door 72) nothing was drawn above it. Repeat the door texture
    upward (as vanilla tiles it) until the step top is reached."""
    d=out/"src/draw.c"; t=d.read_text()
    old="""                if(bot_draw_y == ntop_y_int) {
                    draw_texture_vertical_line(pegged_top_y_int, top_draw_y, ntop_y_int, col_ptr, tex_column);
                } else {
                    draw_bottom_clipped_texture_vertical_line(pegged_top_y_int, top_draw_y, ntop_y_int, bot_draw_y, col_ptr, tex_column);
                }
"""
    if t.count(old)!=1: raise ValueError("draw.c upper-step anchor changed")
    new=old+"""                if (pegged_top_y_int > (s16)top_draw_y) {   /* M14 r073: door header above the texture */
                    s16 hth = ntop_y_int - pegged_top_y_int, htb = pegged_top_y_int;
                    if (hth > 0) {
                        for (u8 hk = 0; hk < 4 && htb > (s16)top_draw_y; hk++) {
                            s16 htt = htb - hth;
                            u16 hyb = (u16)(htb < (s16)bot_draw_y ? htb : (s16)bot_draw_y);
                            if (htb > 0) draw_bottom_clipped_texture_vertical_line(htt, top_draw_y, htb, hyb, col_ptr, tex_column);
                            htb = htt;
                        }
                    }
                }
"""
    d.write_text(t.replace(old,new))
    print("M14 door header tiling installed (draw.c)")

def m14_weapon_sat(out):
    """The sprite attribute table of the weapon was refreshed with DMA_QUEUE, and that queue never
    drains in this engine, so the weapon froze (no bob, no recoil, no fire frame).  Write the SAT
    with the CPU at vblank instead."""
    w=out/"src/weapon_sprites.c"; t=w.read_text()
    n=t.count("VDP_updateSprites(cur_num_sprites, transfer_type);")+t.count("VDP_updateSprites(cur_num_sprites, DMA_QUEUE);")
    assert n==2,n
    t=t.replace("VDP_updateSprites(cur_num_sprites, transfer_type);","m14_sat_update(cur_num_sprites);")
    t=t.replace("VDP_updateSprites(cur_num_sprites, DMA_QUEUE);","m14_sat_update(cur_num_sprites);")
    a="void update_weapon_sprites(TransferMethod transfer_type);"
    assert t.count(a)==1
    t=t.replace(a,a+"""
void m14_sat_update(u16 n) {
    for (;;) { SYS_disableInts(); if (*(volatile u16*)0xC00004 & 8) break; SYS_enableInts(); __asm__ volatile("nop\\n nop\\n nop\\n nop"); }
    VDP_updateSprites(n + 1, CPU);   /* +1: the cleared terminator entry, so no stale sprites stay linked */
    SYS_enableInts();
}""",1)
    k="    FrameVDPSprite* f = frame1->frameVDPSprites;\n    for(int i = 0; i < cur_num_sprites; i++) {"
    assert t.count(k)==1
    t=t.replace(k,"    FrameVDPSprite* f = frame1->frameVDPSprites;\n    u16 m14_cnt = frame1->numSprite < cur_num_sprites ? frame1->numSprite : cur_num_sprites;\n    for(int i = 0; i < m14_cnt; i++) {",1)
    for k,v in (("BASE_WEAPON_X+spr->offsetX, BASE_WEAPON_Y+spr->offsetY,","BASE_WEAPON_X+spr->offsetX, BASE_WEAPON_Y+spr->offsetY+m14_shown_dy,"),
                ("BASE_WEAPON_Y+spr->offsetY+offY","BASE_WEAPON_Y+spr->offsetY+offY+m14_shown_dy")):
        assert t.count(k)==1,k
        t=t.replace(k,v,1)
    # the bob must follow the frame that is actually on screen (cur_sprite_def changes before the SAT is rebuilt)
    k="void update_weapon_sprites(TransferMethod transfer_type) {\n"
    assert t.count(k)==1
    t=t.replace(k,"static AnimationFrame* m14_shown_frame; static s16 m14_shown_dy;\n"+k,1)
    k="    VDP_setSpriteLink(sprite_idx_start+cur_num_sprites, 0);\n"
    assert t.count(k)==1
    t=t.replace(k,k+"    VDP_setSpritePosition(sprite_idx_start+cur_num_sprites, 0, 0);   /* terminator entry is itself drawn: hide the stale sprite in it */\n",1)
    k="    cur_num_sprites = frame->numSprite;\n"
    assert t.count(k)==1
    t=t.replace(k,k+"    m14_shown_frame = frame; m14_shown_dy = (cur_sprite_def == &shotgun_reload) ? -38 : 0;\n",1)
    k="AnimationFrame *frame1 = cur_sprite_def->animations[0]->frames[0];"
    assert t.count(k)==1
    t=t.replace(k,"AnimationFrame *frame1 = m14_shown_frame;\n    if (!frame1) return;",1)
    w.write_text(t)
    g=out/"src/game.c"; t=g.read_text()
    a="    VDP_updateSprites(shotgun_num_sprites, DMA_QUEUE);"
    assert t.count(a)==1
    t=t.replace(a,"    { extern void m14_sat_update(u16 n); m14_sat_update(shotgun_num_sprites); }",1)
    g.write_text(t)
    print("weapon: SAT updated by CPU at vblank")


def m14_weapon(out, wad):
    """MANIFOLD_WEAPON=pistol: replace the Manifold shotgun PNGs with the Doom
    pistol (PISGA0 idle, PISGB0+PISFA0 firing) built from the user's WAD, one
    shared 16-colour palette (index 0 transparent). Also fixes the
    animation table: the compiled reload animation has ONE frame, but
    anim_table asked for frame 1 (a garbage pointer read; harmless in MAME,
    suspected crash on real hardware)."""
    import wad_textures as WT
    from PIL import Image
    w=WT.Wad(wad); rgb=WT.playpal(w)
    def load(name):
        pw,ph,img=WT.patch_image(w.lump(name))
        im=Image.new("RGBA",(pw,ph),(0,0,0,0))
        for y in range(ph):
            for x in range(pw):
                p=img[y][x]
                if p is not None: im.putpixel((x,y),tuple(rgb[p])+(255,))
        return im
    def fit(im,maxw,maxh):
        k=min(1.0,maxw/im.width,maxh/im.height)
        return im if k>=1 else im.resize((max(1,round(im.width*k)),max(1,round(im.height*k))),Image.NEAREST)
    def canvas(parts,w_,h_):
        c=Image.new("RGBA",(w_,h_),(0,0,0,0))
        for im,(cx,by) in parts:      # centre x, bottom y
            c.alpha_composite(im,(max(0,cx-im.width//2),by-im.height)) if by-im.height>=0 else c.alpha_composite(im.crop((0,im.height-by,im.width,im.height)),(max(0,cx-im.width//2),0))
        return c
    idle=canvas([(fit(load("PISGA0"),64,64),(32,64))],64,64)
    # fire frame: true Doom placement (patch left/top offsets), no rescaling.
    # canvas x = X-122 (same as idle), canvas y = Y-66; drawn 38 px higher on screen (m14 weapon Y shift)
    import struct as _st
    def raw(name):
        l=w.lump(name); lo,to=_st.unpack("<hh",l[4:8]); return load(name),-lo,-to
    fire_c=Image.new("RGBA",(64,104),(0,0,0,0))
    for nm in ("PISGB0","PISFA0"):
        im,X,Y=raw(nm)
        fire_c.alpha_composite(im.crop((max(0,122-X),0,im.width,im.height)),(max(0,X-122),Y-66))
    # fire sprite lives on the 64x128 canvas of the original reload resource
    reload_c=Image.new("RGBA",(64,128),(0,0,0,0)); reload_c.alpha_composite(fire_c,(0,0))
    both=Image.new("RGBA",(64,168),(0,0,0,0)); both.alpha_composite(idle,(0,0)); both.alpha_composite(fire_c,(0,64))
    opaque=Image.new("RGB",(64,168),(0,0,0)); opaque.paste(both,(0,0),both)
    mask=[both.getpixel((x,y))[3]>0 for y in range(168) for x in range(64)]
    # 9 colours (indices 1..9): the original weapon palette used 0..9; indices 10..15
    # stay black because the margins/other tiles on PAL0 rely on them.
    pal_img=opaque.quantize(colors=9,method=Image.MEDIANCUT)
    pal=pal_img.getpalette()[:9*3]
    def to_p(rgba):
        o=Image.new("P",rgba.size)
        flat=[0]*(768); flat[3:3+9*3]=pal; o.putpalette(flat)
        px=[]
        pimg=Image.new("RGB",rgba.size,(0,0,0)); pimg.paste(rgba,(0,0),rgba)
        q=pimg.quantize(palette=pal_img,dither=Image.NONE)
        data=[]
        for y in range(rgba.height):
            for x in range(rgba.width):
                data.append(q.getpixel((x,y))+1 if rgba.getpixel((x,y))[3]>0 else 0)
        o.putdata(data); o.info["transparency"]=0
        return o
    d=out/"res/images"
    to_p(idle).save(d/"SHOTGUN.png")
    if os.environ.get("MANIFOLD_WEAPON_FIX","0")=="1":
        to_p(fire_c).save(d/"SHOTGUN_RELOAD.png")          # 64x64 = 64 tiles (was 128)
        rr=out/"res/sprites_res.res"; rt=rr.read_text()
        o2='"images/SHOTGUN_RELOAD.png" 8 16'; n2='"images/SHOTGUN_RELOAD.png" 8 13'
        assert rt.count(o2)==1
        rr.write_text(rt.replace(o2,n2))
    else:
        to_p(reload_c).save(d/"SHOTGUN_RELOAD.png")
    p=out/"src/weapon_sprites.c"
    s=p.read_text()
    old=".anim_idx = 0, .frame_idx = 1,"
    if s.count(old)!=1: raise ValueError("anim_table frame_idx 1 site changed")
    p.write_text(s.replace(old,".anim_idx = 0, .frame_idx = 0,"))
    print("M14 weapon: Doom pistol PNGs written, anim_table frame_idx fixed")

def stage(src, wad, out, control=False):
    out=out.resolve()
    if out.exists():
        raise ValueError("destination already exists: "+str(out))
    shutil.copytree(src,out,ignore=shutil.ignore_patterns(".git","out","__pycache__"))
    skip=set(filter(None,os.environ.get('MANIFOLD_SKIP','').split(',')))
    for step in (stage_missing_resources,normalize_legacy_asm,namespace_legacy_allocators,normalize_legacy_s16_bounds,normalize_legacy_fixed_point_api,normalize_wide_sprite_registers,normalize_legacy_palette_and_asm,normalize_game_integration,normalize_weapon_api_declaration,normalize_remaining_palettes,normalize_menu_callbacks,normalize_math_and_menu,normalize_bitmap_legacy_symbols,normalize_pvs_entry_types,normalize_toggle_declarations,normalize_weapon_sprite_frame_layout,normalize_header_global_definitions,mute_legacy_emulator_debug_logging,restore_generated_scalers_with_correct_constraints,fix_sgdk2_hint_callbacks,harden_inline_asm,fail_loud_on_heap_exhaustion,widen_sector_vertex_buffers,relocate_free_tiles_after_sgdk2_framebuffer,instrument_portal_renderer,default_texture_repetitions,poll_joypad_each_frame,saturate_far_depth_and_guard_windows,clamp_native_vertical_lines,guard_portal_recursion_stack,robust_sector_crossing,guard_zero_reciprocal_in_texture_columns,guard_zero_width_edges,limit_repeated_sector_overdraw,far_portal_fog,fix_fps_font_base,textured_portal_steps,keep_overlays_off_sky,scale_light_distances,hud_fps_and_build_tag,weapon_buffers_fit_vram,):
        if step.__name__ in skip:
            print('SKIPPED stage step:',step.__name__); continue
        step(out)
    if os.environ.get("MANIFOLD_VERT_CACHE","0")=="1":
        cache_transformed_vertices(out)
    if os.environ.get("MANIFOLD_OCCLUSION","0")=="1":
        skip_fully_occluded_portals(out)
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
    map_name=os.environ.get("MANIFOLD_MAP","E1M1")
    map_lumps=read_map(wad,map_name)
    cells, stats, missing=candidate(map_lumps,nodes_from_wad(wad,map_name),allow_gaps=True)
    # Prototype only: missing BSP cut edges are opaque and nontraversable.
    # Never synthesize an unsafe portal or mark this build geometry-validated.
    tex=None
    if os.environ.get("MANIFOLD_CELLS","exact")=="exact" and os.environ.get("MANIFOLD_TEXTURES","1")=="1":
        tex=apply_doom_textures(out,map_lumps,cells,wad)
    m12_things=None
    if os.environ.get("MANIFOLD_OBJECTS","0")=="1":
        if not tex:
            raise ValueError("M12 static sprites require the DOOM map palette")
        from m12_objects import generate, install_templates
        sprite_c, templates, m12_things=generate(wad,map_lumps,cells,tex["vdp_palette"],point_inside)
        (out/"src/m12_doom_objects.c").write_text(sprite_c)
        install_templates(out,templates)
        m12_safe_sprite_raster(out)
    if os.environ.get("MANIFOLD_TEX_U","0")=="1":
        m14_tex_u(out)
    if os.environ.get("MANIFOLD_DOOR_HEADER","1")=="1":
        m14_door_header(out)
    if os.environ.get("MANIFOLD_STAIRS_DOWN","1")=="1":
        m14_stairs_down(out)
    if os.environ.get("MANIFOLD_SPRITE_XFORM","1")=="1":
        m14_sprite_xform(out)
    if os.environ.get("MANIFOLD_WEAPON","")=="pistol":
        m14_weapon(out,wad)
    m12_doors=os.environ.get("MANIFOLD_DOORS","0")=="1"
    (out/"src/e1m1_map.c").write_text(emit(map_lumps,cells,tex,things=m12_things,doors=m12_doors))
    if m12_doors:
        m12_tune_doors(out)
    if os.environ.get("MANIFOLD_DOORS","0")=="2":
        m14_generic_doors(out)
    if os.environ.get("MANIFOLD_SKY_MERGE","0")=="1":
        m13_sky_merge_upper_wall(out)
    # Unified default (user, 10/11): H32 screen + Doom HUD-WAD status bar.
    # MANIFOLD_HUD=manifold / MANIFOLD_H32=0 rebuild the old H40 inventory HUD as a control.
    if os.environ.get("MANIFOLD_HUD","doom")=="doom":
        install_doom_hud(out,wad)
        if os.environ.get("MANIFOLD_HUD_TIMING","0")=="1":
            m13_werk_hud_timing(out)
        if os.environ.get("MANIFOLD_HUD_VRAM_REPAIR","0")=="1":
            m13_werk_hud_vram_repair(out)
    if os.environ.get("MANIFOLD_PICKUPS","0")=="1":
        if m12_things is None or os.environ.get("MANIFOLD_HUD","doom")!="doom":
            raise ValueError("M12 pickups require THINGS and DOOM status bar")
        from m12_pickups import install as install_m12_pickups
        install_m12_pickups(out,templates)
    if os.environ.get("MANIFOLD_VDP_ATOMIC","0")=="1":
        m13_werk_vdp_atomic(out)
    if os.environ.get("MANIFOLD_STATIC_REPAIR_ONCE","0")=="1":
        m13_werk_static_repair_once(out)
    m14_identity(out)
    m14_install_display_hint_variants(out)
    if os.environ.get("MANIFOLD_ALL_KEYS","1")=="1":
        if os.environ.get('MANIFOLD_REAL_KEYS','1')!='1': m14_all_keys(out)
    if os.environ.get("MANIFOLD_LAT_CLIP","0")=="1":
        m14_lat_clip(out)
    if os.environ.get("MANIFOLD_NOHUD","0")=="1":
        m14_nohud(out)
    if os.environ.get("MANIFOLD_VDP_SAFE","0") in ("1","2"):
        m14_vdp_safe(out, int(os.environ["MANIFOLD_VDP_SAFE"]))
    if os.environ.get("MANIFOLD_H32","1")=="1":
        h32_mode(out)
    if os.environ.get("MANIFOLD_MUSIC","0")=="1":
        install_e1m1_music(out)
    if os.environ.get("MANIFOLD_BSP","0")=="1":
        bsp_order_renderer(out)
        if os.environ.get("MANIFOLD_BSP_PRECISION","0")=="1":
            m13_bsp_normal_precision(out)
        if os.environ.get("MANIFOLD_BSP_FILL_DIAG","0")=="1":
            m13_fill_span_diag(out)
        if os.environ.get("MANIFOLD_CLEAR_DIAG","0")=="1":
            m13_clear_diag(out)
        if os.environ.get("MANIFOLD_PROJ_FIX","0")=="1":
            m13_proj_fix(out)
        if os.environ.get("MANIFOLD_BSP_CULL_OFF"):
            m13_cull_off(out)
        if os.environ.get("MANIFOLD_BSP_FAR_FOG","0")=="1":
            m13_bsp_far_fog(out)
        if os.environ.get("MANIFOLD_BSP_ALL_LEAVES","0")=="1":
            m13_bsp_all_leaves_diagnostic(out)
    if os.environ.get("MANIFOLD_TRACE","0")=="1":
        m13_trace(out)
    if os.environ.get("MANIFOLD_FALL","0")=="1":
        m13_fall_snap(out)
    if os.environ.get("MANIFOLD_STABLE_VIEW","0")=="1":
        stable_view(out)
    if os.environ.get("MANIFOLD_RADIUS","0")=="1":
        player_radius_collision(out)
    if os.environ.get("MANIFOLD_NEAR_SAFE","0")=="1":
        m11_safe_near_clipping(out)
    if os.environ.get("MANIFOLD_HUD_REPAIR","0")=="1":
        m11_hud_recompose_diagnostic(out)
    if os.environ.get("MANIFOLD_HIDE_WEAPON","0")=="1":
        m11_hide_weapon_sprites_diagnostic(out)
    if os.environ.get("MANIFOLD_CAMERAS")=="fixed":
        fixed_camera_input(out,cells,map_lumps)
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
    header.write_text(h.replace(old,"#define MAX_WALLS        %d"%int(os.environ.get("MANIFOLD_MAX_WALLS","2048"))))
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
    # r065: the 1 MB wad_area placeholder was never read; reclaiming it frees 1 MB in the shared .common block
    s=s.replace("const uint8_t wad_area[512*1024*2]","const uint8_t wad_area[16]")
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
    # Lower the eye to 64 units in doubled E1M1, preserving foot collision offsets.
    EYE=int(os.environ.get("MANIFOLD_EYE","64"))  # eye above feet, doubled-height units; default unchanged
    eye="(FIX32_FRAC_BITS-4));// + FIX32(50);"
    if s.count(eye)!=1:
        raise ValueError("level.c player z init changed")
    s=s.replace(eye,f"(FIX32_FRAC_BITS-4)) + FIX32({EYE});")
    g=out/"src/game.c"
    gs=g.read_text()
    if gs.count(eye)!=1:
        raise ValueError("game.c rest z changed")
    gs=gs.replace(eye,f"(FIX32_FRAC_BITS-4)) + FIX32({EYE});")
    feet="        s16 cur_player_z = cur_player_pos.z >> (FIX32_FRAC_BITS-4);"
    if gs.count(feet)!=1:
        raise ValueError("game.c collision z changed")
    gs=gs.replace(feet,f"        s16 cur_player_z = (cur_player_pos.z - FIX32({EYE})) >> (FIX32_FRAC_BITS-4); /* feet, not eye */")
    g.write_text(gs)
    old="    cur_player_pos.ang = 0;"
    assert s.count(old)==1
    s=s.replace(old,f"    cur_player_pos.ang = {(angle*1024)//360};")
    p.write_text(s)
    if os.environ.get("MANIFOLD_MONSTERS","0")=="1":
        m14_monsters(out,x,y,angle,spawn_cell)
        if os.environ.get('MANIFOLD_HAZARDS','1')=='1': m14_hazards(out)
        _lp=out/"src/level.c"; _ls=_lp.read_text()
        _an=f"    cur_player_pos.ang = {(angle*1024)//360};"
        assert _ls.count(_an)==1
        _ls=_ls.replace(_an,_an+f"\n    {{ extern s32 m14_spawn_x, m14_spawn_y; extern u16 m14_spawn_cell, m14_spawn_ang; m14_spawn_x = FIX32({x}); m14_spawn_y = FIX32({y}); m14_spawn_cell = {spawn_cell}; m14_spawn_ang = {(angle*1024)//360}; }}")
        _lp.write_text(_ls)
    if os.environ.get("MANIFOLD_START_MENU","0")=="1":
        m14_start_menu(out,x,y,angle,spawn_cell)
        m14_level_exit(out)
    if os.environ.get("MANIFOLD_WEAPON_FIX","0")=="1":
        m14_weapon_fix(out)
        m14_weapon_sat(out)
    if os.environ.get("MANIFOLD_INPUT_FIX","0")=="1":
        m14_input_fix(out)
    if os.environ.get("MANIFOLD_VG_MICRO","0")=="1":
        m14_vg_micro(out)
    if os.environ.get("MANIFOLD_SKIP_CLOSED","0")=="1":
        m14_skip_closed(out)
    if os.environ.get("MANIFOLD_MAX_REVISITS"):
        m14_max_revisits(out,int(os.environ["MANIFOLD_MAX_REVISITS"]))
    if os.environ.get("MANIFOLD_MAX_DEPTH"):
        m14_max_depth(out,int(os.environ["MANIFOLD_MAX_DEPTH"]))
    if os.environ.get("MANIFOLD_UNPACK_MAP","0")=="1":
        m14_unpack_map(out)
    if os.environ.get("MANIFOLD_STATIC_PARAMS","0")=="1":
        m14_static_params(out)
    if os.environ.get("MANIFOLD_DYN_PARAMS","0")=="1":
        m14_dyn_params(out)
    if int(os.environ.get("MANIFOLD_VIEW_TRIM","0"))>0:
        m14_view_trim(out,int(os.environ["MANIFOLD_VIEW_TRIM"]))
    if os.environ.get("MANIFOLD_NO_SOUND","0")=="1":
        m14_no_sound(out)
    if os.environ.get("MANIFOLD_TEX_SPAN","4") in ("8","16"):
        m14_tex_span(out,int(os.environ["MANIFOLD_TEX_SPAN"]))
    report={
        "source":UPSTREAM,"pin":PIN,"map":"E1M1",
        "format":"Manifold portal_map C proof of concept",
        "player_spawn":{"x":x,"y":y,"doom_angle":angle,"manifold_cell":spawn_cell},
        "geometry":stats,"safe_for_runtime":not missing,
        "unpaired_edges_are_solid":len(missing),
        "renderer_unchanged":True,"lighting_color_placeholder":True,
        "thing_spawns_pending":True,"doors_triggers_pending":True
    }
    if os.environ.get("MANIFOLD_WEAPONS","1")=="1" and os.environ.get("MANIFOLD_WEAPON_FIX","0")=="1":
        import m14_wpn_gen; m14_wpn_gen.apply(out,wad)
    if os.environ.get("MANIFOLD_PERF","1")=="1":
        m14_perf(out)
    if os.environ.get("MANIFOLD_FPS_ONLY","0")=="1":
        m14_fps_only(out)
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
