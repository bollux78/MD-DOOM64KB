"""Prepare Z8 original level G_Ticker plus real metadata/P_Init for strict sub link."""
from pathlib import Path
import subprocess

def function_span(text,signature):
    # Select the definition, skipping forward declarations with the same signature.
    start=0
    while True:
        start=text.index(signature,start)
        brace=text.index('{',start)
        semicolon=text.find(';',start,brace)
        if semicolon<0:break
        start+=len(signature)
    depth=1;end=brace+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return start,brace,end

def prepare(tree,objdir,gcc,cflags,common):
    root=common.parent.parent
    game=(root/'src/g_game.c').read_text()
    # Explicit unsupported platform boundaries. Never pretend to load/save SRAM.
    for name in ('G_DoLoadGame','G_DoSaveGame'):
        a,b,c=function_span(game,'static void '+name+'(void)') if 'static void '+name+'(void)' in game else function_span(game,'static void '+name+' (void)')
        game=game[:b]+'{ I_Error("SCD SAVE LOAD UNSUPPORTED"); }'+game[c:]
    if '-DSCD_LIVE' in cflags:
        game+='\nvoid S2D_InitGame(void){G_InitNew(sk_hard,1); }\nvoid S2D_SetCommand(int8_t f,int8_t s,int16_t a,uint8_t b){netcmd.forwardmove=f;netcmd.sidemove=s;netcmd.angleturn=a;netcmd.buttons=b;}\n'
    # Assert that the actual entire G_Ticker body is unchanged from this source.
    original=(root/'src/g_game.c').read_text()
    a,b,c=function_span(original,'void G_Ticker (void)')
    x,y,z=function_span(game,'void G_Ticker (void)')
    assert game[x:z]==original[a:c]
    (objdir/'engine_game.c').write_text(game)
    # Keep real texture-name lookup; no TEXTUREP pixels or renderer init on sub.
    data=(tree/'src/r_data.c').read_text()
    data+='''\nvoid SCD_MetadataInit(void)
{
    const int32_t *names=W_GetLumpByName("TEXTURE1");
    numtextures=*names;
    if(numtextures<=0) I_Error("SCD TEXTURE METADATA");
}
'''
    (objdir/'engine_metadata.c').write_text(data)
    tick=(tree/'src/p_tick.c').read_text()
    anchor='void P_Ticker (void)\n{'
    assert tick.count(anchor)==1
    tick=tick.replace(anchor,anchor+'\n  if(_g_gametic==0){extern void SCD_EngineInitialCheckpoint(void);SCD_EngineInitialCheckpoint();}\n')
    actors='-DSCD_ACTORS' in cflags
    if actors:
        anchor='void P_InitThinkers(void)\n{'
        assert tick.count(anchor)==1
        tick=tick.replace(anchor,anchor+'\n  {extern void S2C_ResetActors(void);S2C_ResetActors();}\n')
    (objdir/'engine_tick.c').write_text(tick)
    sources=[objdir/'engine_tick.c',objdir/'engine_game.c' ,objdir/'engine_metadata.c',
             common/'s1e/engine_platform.c',common/'s1e/engine_libc.c']
    if actors:
        mobj=(tree/'src/p_mobj.c').read_text()
        a,b,c=function_span(mobj,'mobj_t __far* P_SpawnMobj(')
        part=mobj[a:c];assert part.count('return mobj;')==1
        mobj=mobj[:a]+part.replace('return mobj;','{extern void S2C_ActorSpawn(mobj_t *);S2C_ActorSpawn(mobj);} return mobj;')+mobj[c:]
        a,b,c=function_span(mobj,'void P_RemoveMobj(')
        part=mobj[a:c];anchor='  P_UnsetThingPosition (mobj);';assert part.count(anchor)==1
        mobj=mobj[:a]+part.replace(anchor,'  {extern void S2C_ActorRemove(mobj_t *);S2C_ActorRemove(mobj); }\n'+anchor)+mobj[c:]
        (objdir/'engine_mobj.c').write_text(mobj)
        rom=(tree/'src/r24_romthings.c').read_text()
        # Presentation helper only: the RAM sector has no SRAM sector_index.
        rom=rom.replace('uint16_t s=sec->sector_index;', 'uint16_t s=sec-_g_sectors;')
        for suffix in ('RTHING','RMAP','COFF','CIDX','ROFF','RIDX'):
            anchor='sprintf(name,"S%d'+suffix+'",map);'
            assert rom.count(anchor)==1
            rom=rom.replace(anchor,'strcpy(name,"S1'+suffix+'");name[1]=(char)(\'0\'+map);')
        (objdir/'engine_rom.c').write_text(rom+'\n'+(common/'s2c/r24_helpers.inc').read_text())
        sources += [objdir/'engine_mobj.c',objdir/'engine_rom.c',tree/'src/p_maputl.c',common/'s2c/sub_actors.c']
    objects=[]
    # Strip only MD benchmark UI controls from the unmodified core g_game source.
    flags=[f for f in cflags if f!='-DDOOM_R50_PLAY_BENCH']
    for source in sources:
        obj=objdir/(source.stem+'.o')
        subprocess.run([gcc]+flags+['-c',str(source),'-o',str(obj)],cwd=tree,check=True)
        objects.append(obj)
    return objects
