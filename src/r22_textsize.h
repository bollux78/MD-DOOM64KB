#ifndef R22_TEXTSIZE_H
#define R22_TEXTSIZE_H
#include "compiler.h"
#include "doomdef.h"
#if defined(DOOM_R22_PIXEL4)
#define R22_TEXTWIDTH 38
#define R22_TEXTHEIGHT 22
#else
#define R22_TEXTWIDTH VIEWWINDOWWIDTH
#define R22_TEXTHEIGHT VIEWWINDOWHEIGHT
#endif
#endif
