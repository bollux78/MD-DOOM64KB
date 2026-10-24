# R59 COLOR VIEW v3 — six authentic color profiles

**Goal:** Test whether differences among the three R57 A6 modes are intrinsically small, while retaining exact historic A6 behavior. The current R59 v2 has been preserved unchanged on `exp-r59-colorview-runtime`.

The six modes under **Options → Color mode** are:

| Mode | Origin | Expected visual contrast |
|---|---|---|
| CM6 | R58 ColorMatch | Very different CRAM; baseline |
| Balanced | R57 `a6-balanced` | Same A6 CRAM as the next two |
| Tolerant | R57 `a6-tolerant` | Same CRAM and same pair books as Balanced; only a few LUT assignments differ |
| Accents | R57 `a6-accents` | Same A6 CRAM, but more pair/LUT changes |
| A4 Tolerant | R57 `a4-tolerant` | Different A4 CRAM and fewer flat anchors, therefore independently distinguishable |
| A4 Accents | R57 `a4-accents` | Same A4 CRAM, but alternate A4 pairs/LUT |

The original four modes are **NOT** altered to create artificial differences. A4 profiles are generated from the same pinned R57 historical generator, with byte-exact validation.

**Why this experiment exists:** R59 v2 passed source-table tests and BlastEm process tests, but user hardware inspection found that all three A6 modes look equal, whereas CM6 is distinct. This is consistent with the fixed-CRAM R57 design; it does not by itself demonstrate a runtime bug.

**Test:** Use PLAY, same E1M1 position, identical H32/H40 and crop values. Compare CM6 vs Balanced vs A4 Tolerant first. Then compare Balanced vs Tolerant vs Accents and A4 Tolerant vs A4 Accents. H32/H40, crop, audio and benchmark are inherited unchanged from R58.

**Caveat:** No guarantee that A4 is subjectively better; this is a diagnostic contrast and choice of real historical color schemes, not a reoptimization.

**Build workflow:** `.github/workflows/r59-v3-six-modes.yml`. Download `doom-md-r59-colorview-v3-play-perf` when the workflow succeeds.
