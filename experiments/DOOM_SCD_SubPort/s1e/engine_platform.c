/* Headless platform for Z8. UI presentation is silent, unsupported game states
 * fail closed. No spawn, AI, physics, decoder or rebirth is replaced here. */
#include <stdint.h>
#include "doomdef.h"
#include "globdata.h"
#include "st_stuff.h"
#include "hu_stuff.h"
#include "wi_stuff.h"
#include "f_finale.h"
#include "i_system.h"
#include "s_sound.h"
uint8_t r116_nocap; /* original generated spawn-policy configuration */
boolean _g_menuactive;
const boolean nodrawers=true;
gamestate_t wipegamestate=GS_DEMOSCREEN;
void ST_Start(void){}
void ST_Ticker(void){}
void HU_Start(void){}
void HU_Ticker(void){}
void WI_Start(wbstartstruct_t *w){(void)w;I_Error("SCD INTERMISSION UNSUPPORTED");}
void WI_End(void){I_Error("SCD INTERMISSION END UNSUPPORTED");}
void WI_Ticker(void){I_Error("SCD INTERMISSION TIC UNSUPPORTED");}
void F_StartFinale(void){I_Error("SCD FINALE UNSUPPORTED");}
void F_Ticker(void){I_Error("SCD FINALE TIC UNSUPPORTED");}
void D_PageTicker(void){I_Error("SCD TITLE UNSUPPORTED");}
void D_AdvanceDemo(void){I_Error("SCD DEMO END BEFORE BUDGET");}
void S_Start(void){}
