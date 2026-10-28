/* Included by m_text.c after menu helpers are declared. No new persistent state:
 * switches are stored in the existing player.cheats bitfield. */
static void R81_ToggleCheat(int16_t item)
{
    if(_g_gamestate!=GS_LEVEL || !_g_usergame || _g_demoplayback ||
       !_g_player.mo || _g_player.playerstate==PST_DEAD){
        M_StartMessage("START A LIVE GAME FIRST",NULL);return;
    }
    uint16_t bit=item==0?CF_GODMODE:item==1?CF_INFAMMO:CF_NOCLIP;
    _g_player.cheats^=bit;
    if(item==0 && (_g_player.cheats&CF_GODMODE))
        _g_player.health=_g_player.mo->health=100;
    if(item==1 && (_g_player.cheats&CF_INFAMMO)){
        for(uint16_t i=0;i<NUMWEAPONS;i++)_g_player.weaponowned[i]=1;
        /* Shareware has no plasma/BFG/double shotgun artwork or weapon set. */
        _g_player.weaponowned[wp_plasma]=0;
        _g_player.weaponowned[wp_bfg]=0;
        _g_player.weaponowned[wp_supershotgun]=0;
        for(uint16_t i=0;i<NUMAMMO;i++)_g_player.ammo[i]=_g_player.maxammo[i];
        for(uint16_t i=0;i<NUMCARDS;i++)_g_player.cards[i]=true;
        _g_player.armorpoints=200;_g_player.armortype=2;
    }
    if(item==2){
        if(_g_player.cheats&CF_NOCLIP)_g_player.mo->flags|=MF_NOCLIP;
        else _g_player.mo->flags&=~MF_NOCLIP;
    }
}
static void R81_DrawCheats(void)
{
    V_DrawString((R22_TEXTWIDTH-6)/2,3,12,"CHEATS");
    static const char *const labels[3]={"IDDQD  INVINCIBLE","IDKFA  INFINITE AMMO","IDCLIP NO CLIPPING"};
    static const uint16_t bits[3]={CF_GODMODE,CF_INFAMMO,CF_NOCLIP};
    for(uint16_t i=0;i<3;i++){
        M_WriteText(6,(int16_t)(7+i*2),labels[i]);
        M_WriteText(28,(int16_t)(7+i*2),(_g_player.cheats&bits[i])?"ON":"OFF");
    }
    M_WriteText(6,15,"IDKFA: WEAPONS + KEYS");
    M_WriteText(6,17,"A/START: TOGGLE  B: BACK");
}
/* Menu rows have a gap; convert item index 0/2/4 to cheat index 0/1/2. */
static void R81_CheatChoice(int16_t item){R81_ToggleCheat((int16_t)(item/2));}
static const menuitem_t r81_cheat_rows[5]={
    {1,"",R81_CheatChoice},{-1,"",NULL},
    {1,"",R81_CheatChoice},{-1,"",NULL},{1,"",R81_CheatChoice}
};
static const menu_t r81_cheat_def={5,r81_cheat_rows,R81_DrawCheats,6,7,&MainDef,r81_cheats};
static void R81_OpenCheats(int16_t choice){(void)choice;M_SetupNextMenu(&r81_cheat_def);}
