"""Install camera-only MD replay into disposable R128 tree after Z8 build."""
import shutil

def install(tree,common):
    for name in ('md_camera.c','camera_wire.h'):
        shutil.copyfile(common/'s2a'/name,tree/'src'/('s2a_'+name if name.endswith('.c') else name))
    game=tree/'src/g_game.c'
    text=game.read_text()
    text+='''\n/* S2a diagnostic: original local map initialization, no local tick. */
void S2A_InitLocalMap(void){G_InitNew(sk_hard,1);}
'''
    game.write_text(text)
    main=tree/'src/d_main.c'
    text=main.read_text()
    anchor='    D_DoomMainSetup();'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n    {extern void S2A_Run(void);S2A_Run();D_StartTitle();}\n')
    text+='\nvoid S2A_Display(void){D_Display();}\n'
    main.write_text(text)

    menu=tree/'src/m_text.c'
    text=menu.read_text()
    text+='\nvoid S2A_ClearMenus(void){M_ClearMenus();}\n'
    menu.write_text(text)
