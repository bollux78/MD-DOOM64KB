/* Compare final Pair-V tile words outside VBlank, using the existing R115 buffers. */
static inline bool R128_SameRow(const uint16_t *current, const uint16_t *shown, uint16_t width)
{
    uint16_t count = (width >> 1) - 1;
    uint8_t same;
    /* The active viewport is wider than one word. 68000 long reads need even alignment. */
    __asm__ volatile("1: cmpm.l (%0)+,(%1)+\n\t"
                     "dbne %2,1b\n\t"
                     "seq %3"
                     : "+&a"(current), "+&a"(shown), "+&d"(count), "=d"(same)
                     :
                     : "cc", "memory");
    return same && (!(width & 1u) || *current == *shown);
}

static void R128_PrepareBgDma(void)
{
    static uint32_t shown_rect;
    uint32_t skip_a = 0, skip_b = 0;
    const bool eligible = r115_db && r115_show != r115_draw
        && _g_gamestate == GS_LEVEL && !_g_menuactive && !r22_overlay_dirty;
    if (eligible)
    {
        const uint32_t rect = ((uint32_t)r92_rect.y0 << 24) | ((uint32_t)r92_rect.y1 << 16)
            | ((uint32_t)r92_rect.x0 << 8) | r92_rect.x1;
        if (r128_bg_history == R128_BG_PRESENTED && rect == shown_rect)
        {
            const uint16_t width = r92_rect.x1 - r92_rect.x0;
            const uint16_t *current = (const uint16_t *)(const void *)r115_draw;
            const uint16_t *shown = (const uint16_t *)(const void *)r115_show;
            uint32_t bit = 1;
            for (uint16_t y = r92_rect.y0; y < r92_rect.y1; ++y, bit <<= 1)
            {
                const uint16_t offset = y * 76u + r92_rect.x0;
                if (R128_SameRow(current + offset, shown + offset, width))
                    skip_a |= bit;
                if (R128_SameRow(current + offset + 38, shown + offset + 38, width))
                    skip_b |= bit;
            }
        }
        shown_rect = rect;
    }
    r128_bg_history = eligible ? R128_BG_SUBMITTED : R128_BG_INVALID;
    r128_skip_a = skip_a;
    r128_skip_b = skip_b;
}
