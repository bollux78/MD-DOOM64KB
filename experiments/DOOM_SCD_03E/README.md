# 03E resource budget preflight

Run `python3 tools/profile_level.py CONVERTED_R128.wad --source /path/to/src`. The workflow extracts
the exact IWAD from the private R128 All reference using its ELF symbol.
Equal geometry hashes expose aliased levels in that reference.

The report counts aligned, deduplicated map geometry, static wall and sky
patches, texture tables, and the colormap. The last column of byte counts adds
the entire sprite bank as a comparison case. This is not the final blob size.
With `--source`, the E1M1 estimate follows map things and state transitions,
adds known spawned effects and drops, and keeps all supported weapon sprite
families for carryover. It includes paired switch and animated wall textures.
Selection keeps entire sprite families, including all angles. The estimate
excludes generated LUTs, mutable sector data, blob metadata and renderer scratch.
The 448 KiB gate applies to the final blob.

The single-ROM design in §8 of the 03E handoff governs the loader. The host
preflight only measures dependencies. The eventual Mega Drive loader must
stream from its existing IWAD into Program RAM and preserve the 57,920-byte
BSS ceiling. The R128 fallback has its own ten-demo logic and ±2% FPS gate.
