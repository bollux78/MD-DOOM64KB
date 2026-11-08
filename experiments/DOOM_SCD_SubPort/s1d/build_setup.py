#!/usr/bin/env python3
"""S1d-Z4 actual R128 P_SetupLevel geometry-phase ROM, or Z5 full strict-link probe.

Usage: build_setup.py GENERATED_TREE S1B_OUT RAM_OBJECT_DIR PRIVATE_OUT [--full|--ticker]
This modifies ONLY the disposable generated worktree. Nothing is written to
the main checkout or user-approved ROMs. All WAD/ROM objects stay private.
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

if len(sys.argv) not in (5, 6) or (len(sys.argv)==6 and sys.argv[5] not in ("--full", "--ticker", "--compare", "--engine", "--visual", "--world", "--actors", "--live")):
    raise SystemExit("usage: build_setup.py TREE S1B_OUT RAM_OBJECTS OUT [--full|--ticker]")
tree,s1b,ram,out=(Path(s).resolve() for s in sys.argv[1:5])
live=len(sys.argv)==6 and sys.argv[5]=="--live"
actors=len(sys.argv)==6 and sys.argv[5] in ("--actors", "--live")
world=len(sys.argv)==6 and sys.argv[5] in ("--world", "--actors", "--live")
visual=len(sys.argv)==6 and sys.argv[5] in ("--visual", "--world", "--actors", "--live")
engine=len(sys.argv)==6 and sys.argv[5] in ("--engine", "--visual", "--world", "--actors", "--live")
comparison=len(sys.argv)==6 and sys.argv[5]=="--compare"
ticker=len(sys.argv)==6 and sys.argv[5] in ("--ticker", "--compare", "--engine", "--visual", "--world", "--actors", "--live")
full=len(sys.argv)==6
here=Path(__file__).resolve().parent
common=here.parent
out.mkdir(parents=True,exist_ok=True)
objdir=out/"sub"
objdir.mkdir(exist_ok=True)
if engine and (tree/".s1e-md-original/p_tick.c").is_file():
    shutil.copyfile(tree/".s1e-md-original/p_tick.c",tree/"src/p_tick.c")
    shutil.copyfile(tree/".s1e-md-original/r24_romthings.c",tree/"src/r24_romthings.c")
gdk=Path(os.environ.get("SGDK",str(Path.home()/"mars/m68k-elf")))
gcc=str(gdk/"bin/m68k-elf-gcc")
nm=str(gdk/"bin/m68k-elf-nm")
objcopy=str(gdk/"bin/m68k-elf-objcopy")
opt=(tree/"out/.render_options").read_text().split()
defs=[o for o in opt if o.startswith("-D") and not o.startswith(tuple(
    "-D"+d for d in ("DOOM_R22_SRAM_BLOCKLINKS","DOOM_R23_MAPMEM",
    "DOOM_R24_EPISODE","DOOM_R81_SAVE","DOOM_R25_MUSIC")))]
if visual: defs += ["-DSCD_VISUAL", "-I"+str(common/"s2a")]
if world: defs += ["-DSCD_WORLD", "-I"+str(common/"s2b")]
if actors: defs += ["-DSCD_ACTORS", "-DDOOM_R24_EPISODE", "-I"+str(common/"s2c")]
if live: defs += ["-DSCD_LIVE", "-I"+str(common/"s2d")]
if full: defs.append("-DSCD_FULL_SETUP")
if ticker: defs += ["-DSCD_TICKER", "-DDOOM_R47_STATE_HASH"]
cflags=["-DSGDK_GCC","-DDOOM_R23_CPU_PROBE","-I.","-I"+str(tree/"out"),
    "-isystem",str(gdk/"inc"),"-isystem",str(gdk/"lib"),
    "-m68000","-O2","-fno-builtin","-ffreestanding",
    "-fomit-frame-pointer","-fms-extensions","-ffunction-sections",
    "-fdata-sections","-std=gnu11","-w","-I"+str(here),
    "-I"+str(common),"-I"+str(tree/"src"),"-I"+str(tree/"compat")]+defs

# Generated R128 source is compiled with original P_SetupLevel body,
# except two narrowly scoped changes in the GEOMETRY-ONLY experiment:
# (1) drop texture preload that exists purely for the MD renderer;
# (2) stop just after actual P_GroupLines, before thinker/item spawns.
p_setup=(tree/"src/p_setup.c").read_text()
if True:
    # R115_LevelEnd belongs to the MD video double-buffer lifecycle.
    # The sub CPU has no framebuffer and P_SetupLevel starts with an empty
    # renderer state. Remove only this video cleanup call (keep Z_FreeTags).
    hook="{   extern void R115_LevelEnd(void); R115_LevelEnd(); }"
    assert p_setup.count(hook)==1,"R115 MD video cleanup anchor changed"
    p_setup=p_setup.replace(hook,
        "{ /* SCD sub has no R115 video buffers; Z_FreeTags still runs. */ }")
    start_hook="{   extern void R115_LevelStart(void); R115_LevelStart(); }"
    assert p_setup.count(start_hook)==1,"R115 MD framebuffer start anchor changed"
    p_setup=p_setup.replace(start_hook,"{ /* no MD framebuffer on sub */ }")
    anchor='#include "r24_romthings.h"'
    assert p_setup.count(anchor)==1,"p_setup include anchor changed"
    p_setup=p_setup.replace(anchor,anchor+'\n#define P_LoadTexture(t) ((void)0) /* sub no-render only */')
if engine:
    anchor="    R_InitSprites();"
    assert p_setup.count(anchor)==1,"P_Init visual sprite cache anchor changed"
    p_setup=p_setup.replace(anchor,"    /* Sprite graphics remain on MD; switch/animation init above is real. */")
if not full:
    anchor='    P_GroupLines();'
    assert p_setup.count(anchor)==1,"P_GroupLines anchor changed"
    p_setup=p_setup.replace(anchor,anchor+'''
    /* Z4: stop AFTER original geometry loader, BEFORE spawning gameplay.
       The function remains the actual source P_SetupLevel. */
    return;
''')
# No heavy sprintf on bare sub-CPU: equivalent E1M1..E1M9 label generation.
needle='sprintf(lumpname, "E1M%d", map);'
assert p_setup.count(needle)==1,"map label format changed"
p_setup=p_setup.replace(needle,
    "lumpname[0]='E'; lumpname[1]='1'; lumpname[2]='M'; "
    "lumpname[3]=(char)('0'+map); lumpname[4]=0;")
patched=objdir/"p_setup.c"
patched.write_text(p_setup)
parts=[]
for name,source in (("setup",(common/"s2d/sub_live.c" if live else common/"s1e/engine_sub_main.c" if engine else here/("ticker_sub_main.c" if ticker else "setup_sub_main.c"))),
                     ("bsp",here/"setup_bsp_state.c"),
                     ("p_setup",patched)):
    obj=objdir/(name+".o")
    call=subprocess.run([gcc]+cflags+["-c",str(source),"-o",str(obj)],
                        cwd=tree,capture_output=True,text=True)
    if call.returncode:
        print("S1d",name,"C COMPILE FAIL\n"+call.stderr[-8000:],flush=True)
        raise SystemExit(1)
    parts.append(obj)
if full:
    # Copy the genuine nonvisual R128 helpers, not the renderer or approximations.
    # Extract complete named definitions; fail closed if upstream signatures change.
    draw=(tree/"src/r_draw.c").read_text()
    def definition(signature):
        start=draw.index(signature)
        brace=draw.index("{",start)
        depth=1
        end=brace+1
        while depth:
            depth += (draw[end]=="{")-(draw[end]=="}")
            end+=1
        return draw[start:end]
    funcs=["static uint32_t mulu(","fixed_t CONSTFUNC FixedMul(",
           "fixed_t CONSTFUNC FixedMulAngle(",
           "inline static fixed_t CONSTFUNC FixedMul3232(",
           "fixed_t CONSTFUNC FixedMul3216(",
           "static uint32_t R10_ReciprocalSmall(",
           "fixed_t CONSTFUNC FixedApproxDiv(",
           "static PUREFUNC int16_t R_PointOnSide(",
           "subsector_t __far* R_PointInSubsector(",
           "static CONSTFUNC int16_t SlopeDiv(",
           "CONSTFUNC angle_t R_PointToAngle3("]
    # Angle table is private to r_draw.c (not tables.c); keep exact values.
    angle_start=draw.index("static const angle_t tantoangleTable[2049] =")
    angle_end=draw.index("};",angle_start)+2
    angle_table=draw[angle_start:angle_end]
    utility=objdir/"sub_geometry.c"
    utility.write_text(draw[:draw.index("#include <stdint.h>")]+
        '#include "compiler.h"\n#include "r_main.h"\n#include "globdata.h"\n'+
        '#include "m_fixed.h"\n#include "tables.h"\n#include "r47_mul.h"\n'+
        '#define SLOPERANGE 2048\nuint16_t validcount=1;\n'+
        angle_table+'\n#define tantoangle(t) tantoangleTable[t]\n'+
        "\n\n".join(definition(sig) for sig in funcs))
    # Silent hardware boundary only. No gameplay function is substituted.
    audio=objdir/"sub_silent_audio.c"
    audio.write_text('#include "s_sound.h"\n'
        'void S_StartSound(mobj_t *o,sfxenum_t s){(void)o;(void)s;}\n'
        'void S_StartSound2(degenmobj_t *o,sfxenum_t s){(void)o;(void)s;}\n'
        'void S_StopSound(void *o){(void)o;}\n')
    switch=objdir/"p_switch.c"
    switch_text=(tree/"src/p_switch.c").read_text()
    # Texture warming is a renderer side effect; switch gameplay remains real.
    switch_text=re.sub(r"R_GetTexture\(([^;]+)\);",r"(void)(\1);",switch_text)
    switch.write_text(switch_text)
    for name,source in (("sub_geometry",utility),("sub_audio",audio),("p_switch",switch),
                        ("am_map",tree/"src/am_map.c"),
                        ("r_sky",tree/"src/r_sky.c")):
        obj=objdir/(name+".o")
        result=subprocess.run([gcc]+cflags+["-c",str(source),"-o",str(obj)],
                              cwd=tree,capture_output=True,text=True)
        if result.returncode:
            print(result.stderr,flush=True)
            raise SystemExit("Z5 platform compile failed: "+name)
        parts.append(obj)
if ticker:
    for name in ("m_random", "r_plane", "scd_sub_system"):
        source=(here if name=="scd_sub_system" else tree/"src")/(name+".c")
        obj=objdir/(name+".o")
        subprocess.run([gcc]+cflags+[("-DSCD_SUB_ZONE_BYTES=131072" if actors else ("-DSCD_SUB_ZONE_BYTES=196608" if world else "-DSCD_SUB_ZONE_BYTES=229376")), "-c",str(source),"-o",str(obj)],cwd=tree,check=True)
        parts.append(obj)
if world:
    source=common/"s2b/sub_world.c"
    obj=objdir/"sub_world.o"
    subprocess.run([gcc]+cflags+["-c",str(source),"-o",str(obj)],cwd=tree,check=True)
    parts.append(obj)
if engine:
    sys.path.insert(0,str(common/"s1e"))
    from engine_build import prepare
    parts += prepare(tree,objdir,gcc,cflags,common)
base=s1b/"sub"
kept=[base/name for name in ("boot.o","libc.o","scd_sub_transport.c.o",
                             "scd_sub_w_wad.c.o")]
kept += [ram/name for name in ("p_tick.o","g_game.o","z_zone.o","scd_sub_system.o") if not ((ticker and name=="scd_sub_system.o") or (engine and name in ("p_tick.o","g_game.o")))]
for obj in kept:
    if not obj.is_file(): raise SystemExit("Missing object: "+str(obj))
if live:
    kept=[p for p in kept if p.name!='scd_sub_transport.c.o']
    obj=objdir/'live_transport.o'
    subprocess.run([gcc]+cflags+['-c',str(common/'scd_sub_transport.c'),'-o',str(obj)],cwd=tree,check=True)
    parts.append(obj)
objs=[str(x) for x in kept+parts]
if full:
    for path in sorted(ram.glob("*.o")):
        if path.name not in ("p_setup.o","p_tick.o","g_game.o",
                            "z_zone.o","scd_sub_system.o",
                            "scd_sub_transport.o","scd_sub_w_wad.o",
                            "logic-slice.o","p_switch.o") and not (ticker and path.name in ("m_random.o", "r89_ai.o")):

            if actors and path.name in ("p_mobj.o","p_maputl.o","r24_romthings.o"): continue
            objs.append(str(path))

libgcc=subprocess.check_output([gcc,"-m68000","-print-libgcc-file-name"],
                               text=True).strip()
elf=objdir/("full.elf" if full else "geometry.elf")
link=[gcc,"-m68000","-nostdlib","-Wl,--gc-sections",
      "-Wl,-e,subcpu_vectors",("-Wl,-T,"+str(common/"s1e/sub_engine.ld") if engine else "-Wl,-Ttext=0"),
      "-Wl,-Map,"+str(objdir/"setup.map"),"-o",str(elf)]+objs+[libgcc]
p=subprocess.run(link,capture_output=True,text=True)
report=dict(phase="Z5 full P_SetupLevel STRICT diagnostic — not a ROM" if full
       else "Z4 actual P_SetupLevel geometry phase",linked=p.returncode==0,
       errors=p.stderr,object_count=len(objs),
       undefined_symbols=sorted(set(re.findall(r"undefined reference to [`\"]([^\'\"]+)[\'\"]",p.stderr))))
(out/"link_report.json").write_text(json.dumps(report,indent=2)+"\n")
print("S1d",("Z5" if full else "Z4"),"strict link:",
      "PASS" if p.returncode==0 else "FAIL", "objects",len(objs),flush=True)
if p.returncode:
    print(p.stderr,flush=True)
    raise SystemExit(1)
symbols={}
for row in subprocess.check_output([nm,str(elf)],text=True).splitlines():
    v=row.split()
    if len(v)==3:
        try: symbols[v[2]]=int(v[0],16)
        except ValueError: pass
for root in (("G_Ticker","P_Init",("S2D_SetCommand" if live else "G_DeferedPlayDemo")) if engine else ()) + ("subcpu_vectors","P_SetupLevel","P_InitThinkers") + (("P_Ticker", "P_PlayerThink", "P_MobjThinker") if ticker else ()):
    if root not in symbols: raise SystemExit("Missing linked runtime root: "+root)
if symbols["subcpu_vectors"]!=0: raise SystemExit("bad boot vector")
if symbols.get("_end",0)>=(0x68000 if actors else (0x74000 if world else (0x7C000 if ticker else 0x7E000))): raise SystemExit("sub PRG-RAM end exceeds stack reserve")
binary=objdir/"setup.bin"
subprocess.run([objcopy,"-O","binary","-R",".bss",
                str(elf),str(binary)],check=True)
if binary.stat().st_size>128*1024:
    raise SystemExit("setup payload exceeds existing S1b single-window loader")
print("S1d linked sub image bytes",binary.stat().st_size,
      "RAM end",hex(symbols["_end"]),flush=True)
name="doom-md-scd-s1d-z5" if full else "doom-md-scd-s1d-z4"
marker="0x5A6Du" if full else "0x5A5Du"
if ticker:
    name="doom-md-scd-s1e-z6"
    marker="0x5A7Du"

# Reuse trusted S1b boot and gameplay fallback, packaging private diagnostic ROM.
subprocess.run(["python3",str(common.parent/
    "DOOM_SCD_Bench03D_Transport/tools/make_sub_header.py"),
    str(binary),str(tree/"src/s1b_sub.h")],check=True)
md=(common/"s1b/s1b_md.c").read_text()
needle="for(u16 i=1;i<=3;i++)"
assert md.count(needle)==1
md=md.replace(needle,"for(u16 i=1;i<=9;i++)")
needle="    REPORT=r;"
assert md.count(needle)==1
md=md.replace(needle,
    "    r.reserved=(r.stage==5 || r.stage==6)?*(volatile const u16*)0xA12024:0;\n"
    +needle)
# S1b's 4-request check must be replaced for the E1M1 9-lump test.
needle="const bool pass=r.stage==5 && r.serviced==4"
assert md.count(needle)==1,"S1b acceptance predicate changed"
md=md.replace(needle,
    "const bool pass=r.reserved=="+marker+" && r.stage==5 && r.serviced==10")
assert md.count("r.serviced==4")==0
assert md.count("r.serviced==10")==1
needle='VDP_drawText("S1B SUB WAD TRANSPORT",1,2);'
assert md.count(needle)==1
md=md.replace(needle,
    'VDP_drawText("S1D Z4 REAL P_SETUP GEOM",1,2);\n'
    '    VDP_drawText(r.reserved==0x5A5Du?"SETUP PASS":"SETUP FAIL",1,11);')
if full:
    md=md.replace("S1D Z4 REAL P_SETUP GEOM","S1D Z5 FULL P_SETUP")
    md=md.replace("r.reserved==0x5A5Du", "r.reserved=="+marker)
if ticker:
    md=md.replace("S1D Z5 FULL P_SETUP", "S1E Z6 SUB P_TICKER 2600")
    md=md.replace("    REPORT=r;", """    if((r.stage==5 && r.reserved==0x5A7Du) || r.stage==6){
        CD_SUB_BYTE=3; /* halt sub and request PRG-RAM bus after completion */
        if(!wait_sub(2,2)){r.stage=7;}else{
            if(r.stage==6 && r.sub_crc<0x80000UL){
                const u32 ep=r.sub_crc;
                CD_MEMCTRL=(CD_MEMCTRL & 0xFF3Fu)|((ep>>11)&0xC0u);
                volatile const u8 *msg=(volatile const u8 *)(0x420000UL+(ep&0x1FFFFUL));
                volatile u8 *err=(volatile u8 *)0x61D000;
                for(u16 i=0;i<128;i++)err[i]=msg[i];
            }
            CD_MEMCTRL=(CD_MEMCTRL & 0xFF3Fu)|0x00C0u;
            volatile const u16 *src=(volatile const u16 *)0x43C000;
            volatile u16 *dst=(volatile u16 *)0x61E000;
            for(u16 i=0;i<27u*8u*2u;i++)dst[i]=src[i];
        }
    }
    REPORT=r;""")
    md=md.replace("SETUP PASS", "2600 TICS PASS")
    md=md.replace("r.serviced==10", "r.serviced==11")
    md=md.replace("spins<50000000UL", "spins<500000000UL")
    md=md.replace("r.md_crc==r.sub_crc", "r.sub_crc!=0")
    md=md.replace('sprintf(t,"MD CRC %08lX",(unsigned long)r.md_crc);',
                  'sprintf(t,"INPUT DTE1M1 / AI NORMAL");')
    md=md.replace('sprintf(t,"CD CRC %08lX",(unsigned long)r.sub_crc);',
                  'sprintf(t,"STATE HASH %08lX",(unsigned long)r.sub_crc);')
if comparison:
    backup=tree/".s1e-md-original"
    backup.mkdir(exist_ok=True)
    for filename in ("g_game.c","d_main.c","m_text.c","m_random.c","p_tick.c","r24_romthings.c"):
        shutil.copyfile(tree/"src"/filename,backup/filename)
    name="doom-md-scd-s1e-z7"
    md=md.replace("S1E Z6 SUB P_TICKER 2600", "S1E Z7 MD SUB TRACE")
    shutil.copyfile(common/"s1e/md_observer.c",tree/"src/s1e_md_observer.c")
    game=tree/"src/g_game.c"
    text=game.read_text()
    anchor="        P_Ticker ();"
    assert text.count(anchor)==1,"G_Ticker P_Ticker observer anchor changed"
    text=text.replace(anchor, """        { extern void S1E_MDObserve(uint16_t);
          S1E_MDObserve(0);
          P_Ticker();
          S1E_MDObserve(1); }
""")
    game.write_text(text)
    main=tree/"src/d_main.c"
    text=main.read_text()
    anchor="    D_DoomMainSetup();"
    assert text.count(anchor)==1,"MD setup observer anchor changed"
    text=text.replace(anchor,anchor+"""
    /* Z7 diagnostic only: invoke the exact existing menu benchmark action. */
    { extern void S1E_MDStart(void); S1E_MDStart(); }
""")
    main.write_text(text)
    menu=tree/"src/m_text.c"
    text=menu.read_text()
    assert "static void M_R116Run(int16_t choice)" in text
    menu.write_text(text+"""
void S1E_MDStart(void)
{
    extern volatile uint8_t r116_norender;
    *(volatile uint32_t *)0x61C030UL=0;
    *(volatile uint32_t *)0x61C034UL=0xFFFFFFFFUL;
    R89_SetAIMode(0);r116_norender=1;
    M_R116Run(1);
}
""")
    random=tree/"src/m_random.c"
    text=random.read_text()
    assert text.count("#if defined(DOOM_R47_STATE_HASH)")==1
    random.write_text(text.replace("#if defined(DOOM_R47_STATE_HASH)","#if 1 /* read-only MD trace observer */"))
if engine:
    backup=tree/".s1e-md-original"
    if backup.is_dir():
        # Z7's automatic headless MD benchmark is instrumentation only. The
        # Z8 console ROM must retain the original R128 menu/game after START.
        for filename in ("g_game.c","d_main.c","m_text.c","m_random.c","p_tick.c","r24_romthings.c"):
            shutil.copyfile(backup/filename,tree/"src"/filename)
    for artifact in (tree/"src/s1e_md_observer.c",
                     tree/"out/release/src/s1e_md_observer.o",
                     tree/"out/release/_deps/src/s1e_md_observer.d"):
        artifact.unlink(missing_ok=True)
    for filename in ("s2a_md_camera","s2b_md_world","s2c_md_actors","s2d_md_live"):
        for artifact in (tree/"src"/(filename+".c"),tree/"out/release/src"/(filename+".o"),tree/"out/release/_deps/src"/(filename+".d")):
            artifact.unlink(missing_ok=True)
    name="doom-md-scd-s1e-z8"
    md=md.replace("S1E Z6 SUB P_TICKER 2600", "S1E Z8 REAL G_TICKER")
    md=md.replace("0x5A7Du", "0x5A8Du")
    md=md.replace("r.serviced==11", "r.serviced==12")
    md=md.replace("27u*8u*2u", "27u*8u*2u+8u")
    md=md.replace("2600 TICS PASS", "2600 TICS AND REBIRTH PASS")
if visual:
    name="doom-md-scd-s2a-camera"
    md=md.replace("S1E Z8 REAL G_TICKER", "S2A SUB CAMERA READY")
    anchor="    REPORT=r;"
    assert md.count(anchor)==1
    md=md.replace(anchor,"""    if(r.stage==5 && r.reserved==0x5A8Du){
        volatile const u16 *cam=(volatile const u16 *)0x43C400;
        volatile u16 *dst=(volatile u16 *)0x61A000;
        for(u16 i=0;i<0x390u/2u;i++)dst[i]=cam[i];
    }
    REPORT=r;""")
    sys.path.insert(0,str(common/"s2a"))
    from visual_build import install
    install(tree,common,world=world,actors=actors)
if world:
    name="doom-md-scd-s2b-world"
    md=md.replace("S2A SUB CAMERA READY", "S2B SUB WORLD READY")
    anchor="    REPORT=r;"
    assert md.count(anchor)==1
    md=md.replace(anchor,"""    if(r.stage==5 && r.reserved==0x5A8Du){
        volatile const u32 *head=(volatile const u32 *)0x434000UL;
        const u32 used=head[5];
        if(head[0]!=0x53325742UL || used<256u || used>32768u || used%4u){r.stage=8;}
        else{
            volatile const u16 *src=(volatile const u16 *)0x434000UL;
            volatile u16 *dst=(volatile u16 *)0x600000UL;
            for(u16 i=0;i<used/2u;i++)dst[i]=src[i];
        }
    }
    REPORT=r;""")
if actors:
    name="doom-md-scd-s2c-actors"
    md=md.replace("r.serviced==12", "r.serviced==18")
    md=md.replace("S2B SUB WORLD READY","S2C SUB ACTORS READY")
    anchor="    REPORT=r;"
    assert md.count(anchor)==1
    md=md.replace(anchor,"""    if(r.stage==5 && r.reserved==0x5A8Du){
        volatile const u32 *head=(volatile const u32 *)0x428000UL;
        const u32 used=head[4];
        if(head[0]!=0x53324342UL || used<256u || used>49152u || used%4u){r.stage=8;}
        else{
            volatile const u16 *src=(volatile const u16 *)0x428000UL;
            volatile u16 *dst=(volatile u16 *)0x608000UL;
            for(u16 i=0;i<used/2u;i++)dst[i]=src[i];
        }
    }
    REPORT=r;""")
if live:
    sys.path.insert(0,str(common/'s2d'))
    import live_build
    live_build.install(tree,common)
    md=live_build.boot(common)
    name='doom-md-scd-s2d-live'
(tree/"src/s1b_md.c").write_text(md)
env=dict(os.environ,PATH=str(gdk/"bin")+":"+os.environ["PATH"])
subprocess.run(["make","GDK="+str(gdk),"PREFIX=m68k-elf-","JAVA=java",
                "EXTRA_FLAGS=-Isrc -Icompat -std=gnu11 "+" ".join(
                    o for o in opt if o.startswith("-D")),
                "LIBGCC="+libgcc+" -lgcc"],
               cwd=tree,env=env,check=True)
rom=out/(name+".bin")
linear=out/"linear.bin"
subprocess.run(["python3","scripts/lab/finish_r35_rom.py",
                "out/rom.bin",str(linear)],check=True,cwd=tree)
subprocess.run(["python3",str(common.parent/
    "DOOM_SCD_Bench03D_Transport/tools/mark_mode1.py"),
    str(linear),str(rom)],check=True)
subprocess.run(["python3",str(common.parent/
    "DOOM_SCD_03E/rom_identity.py"),str(rom)],check=True)
linear.unlink()
shutil.copyfile(tree/"out/release/rom.out",out/(name+".elf"))
print("S1d Z5 private ROM:" if full else "S1d Z4 private ROM:",rom,flush=True)
