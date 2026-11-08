/* N1 link probe: MD-only hooks the R128 renderer calls, stubbed for the sub. Signatures are
 * placeholders for the link report; the real N2 program replaces them with checked ones. */
#include <stdint.h>
#include "doomdef.h"
#include "r57_viewport.h"
#if defined(DOOM_R57_CROP16) && defined(DOOM_R57_VIEW_MENU)
R57ViewConfig r57_view = {0, 0, 0, 2, 76, 2, 44};
#endif
volatile uint32_t _g_vblankCount;
void R64A_FrameBegin(void) {}
void R64A_FrameEnd(void) {}
void R95_FlatSetup(void) {}
void R96_WallSetup(void) {}
void R115_LevelStart(void) {}
void R115_LevelEnd(void) {}
void R117_LoadDone(void) {}
void I_BenchmarkReset(void) {}
void I_BenchmarkShowResults(void) {}
void I_BenchmarkWindowReset(void) {}
void DMX_Play(int id, int16_t ch) { (void)id; (void)ch; }
void I_PlaySong(int h, int loop) { (void)h; (void)loop; }
void I_StopSong(int h) { (void)h; }
void SYS_doVBlankProcess(void) {}
void *R81_SaveScratch(void) { return 0; }
#include <stdarg.h>
/* Small vsprintf for engine lump names and messages: %d %i %u %x %X %c %s, 'l' prefix, width,
 * zero padding and precision (%.8s). */
int vsprintf(char *out, const char *f, va_list ap)
{
    char *o = out;
    while (*f)
    {
        if (*f != '%') { *o++ = *f++; continue; }
        f++;
        char pad = ' '; int width = 0, prec = -1, lng = 0;
        if (*f == '0') { pad = '0'; f++; }
        while (*f >= '0' && *f <= '9') width = width * 10 + (*f++ - '0');
        if (*f == '.') { f++; prec = 0; while (*f >= '0' && *f <= '9') prec = prec * 10 + (*f++ - '0'); }
        while (*f == 'l' || *f == 'h') { lng |= *f == 'l'; f++; }
        char buf[16]; int n = 0; const char *str = 0;
        switch (*f)
        {
        case 'd': case 'i': {
            long v = lng ? va_arg(ap, long) : va_arg(ap, int);
            unsigned long u = v < 0 ? (unsigned long)-v : (unsigned long)v;
            do buf[n++] = (char)('0' + u % 10u); while (u /= 10u);
            if (v < 0) buf[n++] = '-';
            break; }
        case 'u': case 'x': case 'X': {
            unsigned long u = lng ? va_arg(ap, unsigned long) : va_arg(ap, unsigned int);
            const unsigned base = *f == 'u' ? 10u : 16u;
            do { unsigned d = (unsigned)(u % base); buf[n++] = (char)(d < 10 ? '0' + d : (*f == 'x' ? 'a' : 'A') + d - 10); } while (u /= base);
            break; }
        case 'c': buf[n++] = (char)va_arg(ap, int); break;
        case 's': str = va_arg(ap, const char *); if (!str) str = "(null)"; break;
        case '%': buf[n++] = '%'; break;
        default: buf[n++] = *f ? *f : '?'; break;
        }
        if (*f) f++;
        if (str)
        {
            int len = 0; while (str[len] && (prec < 0 || len < prec)) len++;
            for (int k = len; k < width; k++) *o++ = ' ';
            for (int k = 0; k < len; k++) *o++ = str[k];
        }
        else
        {
            for (int k = n; k < width; k++) *o++ = pad;
            while (n) *o++ = buf[--n];
        }
    }
    *o = 0;
    return (int)(o - out);
}
int sprintf(char *b, const char *f, ...) { va_list ap; va_start(ap, f); int n = vsprintf(b, f, ap); va_end(ap); return n; }
/* Formatted I_Error for the sub: the MD reads the text through a bus request (N2+). Linked before
 * scd_sub_system.c, so this definition wins. */
static char scd_error_text[64];
_Noreturn void I_Error(const char *message, ...)
{
    va_list ap; va_start(ap, message); vsprintf(scd_error_text, message, ap); va_end(ap);
    *(volatile uint16_t *)0xFF802AUL = (uint16_t)((uint32_t)(uintptr_t)scd_error_text >> 16);
    *(volatile uint16_t *)0xFF802CUL = (uint16_t)(uintptr_t)scd_error_text;
    *(volatile uint16_t *)0xFF8020UL = 0xDEADu;
    for (;;) {}
}
