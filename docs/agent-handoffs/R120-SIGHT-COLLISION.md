# R120 — Sight + collision A/B

Branch: `exp-chatgpt-r120-sight-collision-20261103`. Baseline: R119 `both` (includes R118 `mulvc`, R119 secnodes and collision).

| Set | Change |
| --- | --- |
| control | R119 both, untouched |
| sight | Converts fixed-point LOS bbox comparisons to mathematically exact floor/ceil thresholds once per subsector; defers mapline pointer until after validcount |
| collision | Exact floor/ceil clipping checks in PIT_CheckLine; preserves inclusive boundaries |
| both | sight + collision |

All changes are experimental and should only be kept if RAM sizes equal, 10-demo logic signatures identical, shadow-off and shadow-on pixel comparisons identical, and A/B measurements justify them. Zero new .data/.bss permitted.

The workflow saves private ROMs/ELFs under `/home/dan/Projetos/Personal/r120-sight-collision/run-<runid>-1/c-{control,sight,collision,both}/`. Only reports appear in GitHub artifacts. Standard user bench: PLAY → Benchmark → Run All Demos in Sequence; NTSC 60Hz 7.67MHz H40 default crop AI Normal Shadow Off. Do not merge to stable automatically.
