/* Pair-V row reuse probe. Signatures are diagnostic only; DMA is unchanged. */
#if !defined(DOOM_R48_PAIR_V) || !defined(DOOM_R57_CROP16)
#error Pair-V row probe requires the R128 viewport
#endif

static void R128_BGProbe(void)
{
    static uint32_t previous[21];
    static uint32_t window_start;
    static uint16_t same_rows, total_rows;
    static uint32_t previous_rect;

    if (_g_gamestate != GS_LEVEL || r22_overlay_dirty)
    {
        r128_bg_presented = false;
        same_rows = total_rows = 0;
        window_start = _g_vblankCount;
        return;
    }

    const uint16_t first = r57_queued_crop ? R57_TILE_YMIN : 1;
    const uint16_t end = r57_queued_crop ? R57_TILE_YEND : 22;
    const uint16_t left = r57_queued_crop ? R57_TILE_XMIN : 0;
    const uint16_t width = r57_queued_crop ? R57_DMA_WORDS : 38;
    const uint32_t rect = ((uint32_t)first << 16) | (end << 11) | (left << 6) | width;
    const bool comparable = r128_bg_presented && rect == previous_rect;
    const uint16_t *map = (const uint16_t *)(const void *)r22_fb.pixels;

    for (uint16_t y = first; y < end; ++y)
    {
        const uint16_t *row = map + y * 76 + left;
        uint32_t hash = 0x811C9DC5u;
        for (uint16_t x = 0; x < width; ++x)
        {
            hash = ((hash << 7) | (hash >> 25)) + row[x];
            hash = ((hash << 7) | (hash >> 25)) + row[38 + x];
        }
        if (comparable && hash == previous[y - 1])
            ++same_rows;
        previous[y - 1] = hash;
    }
    if (comparable)
        total_rows += end - first;
    previous_rect = rect;
    r128_bg_presented = false;

    const uint32_t now = _g_vblankCount;
    if (now - window_start >= 60u)
    {
        char label[] = "BG SAME 000%";
        if (total_rows)
        {
            const uint16_t pct = (same_rows * 100u + total_rows / 2u) / total_rows;
            label[8] += pct / 100;
            label[9] += pct / 10 % 10;
            label[10] += pct % 10;
        }
        else
        {
            label[8] = label[9] = label[10] = '-';
        }
        R22_DrawText(VDP_BG_A, label, 1, 0);
        window_start = now;
        same_rows = total_rows = 0;
    }
}
