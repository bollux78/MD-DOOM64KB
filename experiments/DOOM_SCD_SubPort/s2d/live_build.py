"""Install continuous snapshot/input endpoint into disposable R128 tree."""
import shutil

def install(tree,common,fast=False):
    # Reuse native local initialization and presentation helpers, keeping original
    # engine bodies. Replace only the offline camera runner's startup call.
    main=tree/'src/d_main.c';s=main.read_text();anchor='extern void S2A_Run(void);S2A_Run();'
    assert s.count(anchor)==1
    main.write_text(s.replace(anchor,'extern void S2D_Run(void);S2D_Run();'))
    (tree/'src/s2a_md_camera.c').unlink()
    for p in (tree/'out/release/src/s2a_md_camera.o',tree/'out/release/_deps/src/s2a_md_camera.d'):p.unlink(missing_ok=True)
    for name in ('live_wire.h','md_live.c'):
        shutil.copyfile(common/'s2d'/name,tree/'src'/('s2d_'+name if name.endswith('.c') else name))
    if fast:
        p=tree/'src/s2d_md_live.c';p.write_text('#define SCD_FAST 1\n'+p.read_text())
    for name in ('s2b_md_world.c','s2c_md_actors.c','scd_md_server.c'):
        p=tree/'src'/name;p.write_text(('#define SCD_FAST 1\n' if fast else '')+'#define SCD_LIVE 1\n'+p.read_text())

def boot(common,fast=False):
    s=(common/'s1b/s1b_md.c').read_text()
    s=s.replace('    if(!boot_sub())','    *(volatile u16 *)0xA12010=0;\n    if(!boot_sub())')
    s=s.replace('    REPORT=r;','    r.reserved=*(volatile const u16 *)0xA12024;\n    REPORT=r;')
    s=s.replace('r.serviced==4','r.serviced==18 && r.reserved==0x5A9D')
    s=s.replace('r.md_crc==r.sub_crc','r.stage==5')
    s=s.replace('S1B SUB WAD TRANSPORT','S2D LIVE SUB LOGIC READY')
    s=s.replace('START: PLAY R128 ON MEGA DRIVE','START: PLAY ON SEGA CD')
    s=s.replace('sprintf(t,"MD CRC %08lX",(unsigned long)r.md_crc);','sprintf(t,"LIVE INPUT / E1M1 / AI NORMAL");')
    s=s.replace('sprintf(t,"CD CRC %08lX",(unsigned long)r.sub_crc);','sprintf(t,"ONE STATE PER TIC / PROTOTYPE");')
    if fast:s=s.replace('S2D LIVE SUB LOGIC READY','S2E FAST LIVE SUB LOGIC').replace('0x5A9D','0x5AAD').replace('ONE STATE PER TIC / PROTOTYPE','DELTA WORLD / CHECKED WORD COPIES')
    return s
