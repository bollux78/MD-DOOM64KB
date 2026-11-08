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
    (objdir/'engine_tick.c').write_text(tick)
    sources=[objdir/'engine_tick.c',objdir/'engine_game.c' ,objdir/'engine_metadata.c',
             common/'s1e/engine_platform.c',common/'s1e/engine_libc.c']
    objects=[]
    # Strip only MD benchmark UI controls from the unmodified core g_game source.
    flags=[f for f in cflags if f!='-DDOOM_R50_PLAY_BENCH']
    for source in sources:
        obj=objdir/(source.stem+'.o')
        subprocess.run([gcc]+flags+['-c',str(source),'-o',str(obj)],cwd=tree,check=True)
        objects.append(obj)
    return objects
