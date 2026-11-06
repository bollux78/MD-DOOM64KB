# 03E resource budget preflight

Run `python3 tools/profile_level.py CONVERTED_R128.wad`. The workflow extracts
the exact IWAD from the private R128 All reference using its ELF symbol.
Equal geometry hashes expose aliased levels in that reference.

The report counts aligned, deduplicated map geometry, static wall and sky
patches, texture tables, and the colormap. The last column of byte counts adds
the entire sprite bank as a comparison case. This is not the final blob size.
The report excludes sprite selection, texture changes and animation closure,
generated LUTs, mutable sector data, blob metadata and renderer scratch.
The 448 KiB gate applies to the final blob. Keep the full sprite bank out of
the initial loader and measure the selected dependencies before E1.

The single-ROM design in §8 of the 03E handoff governs the loader. The host
preflight only measures dependencies. The eventual Mega Drive loader must
stream from its existing IWAD into Program RAM and preserve the 57,920-byte
BSS ceiling. The R128 fallback has its own ten-demo logic and ±2% FPS gate.
