# M14 — lista de ROMs entregues (E1M1 Manifold)

As ROMs foram compiladas na sessão do Claude e entregues como arquivo no chat; **os binários não estão no GitHub**. O GitHub (branch `exp-manifold-m14-e1m1`) guarda o código e a documentação; qualquer ROM pode ser refeita com `experiments/DOOM_Manifold_E1M1/tools/m14/build_local.sh NOME VARIAVEIS...`.

Base comum: `MANIFOLD_BSP=0 MANIFOLD_RADIUS=1 MANIFOLD_STABLE_VIEW=1 MANIFOLD_H32=0 MANIFOLD_HUD_TIMING=1 MANIFOLD_HUD_VRAM_REPAIR=0 MANIFOLD_VDP_ATOMIC=0 MANIFOLD_STATIC_REPAIR_ONCE=1 MANIFOLD_NEAR_SAFE=1 MANIFOLD_SKY_MERGE=1 MANIFOLD_SKY_CEIL_UNIFORM=0 MANIFOLD_OBJECTS=1 MANIFOLD_PICKUPS=1 MANIFOLD_DOORS=1 MANIFOLD_EYE=48 MANIFOLD_TEX_U=1 MANIFOLD_TEX_HSTRETCH=1.0 MANIFOLD_WEAPON=pistol`

| arquivo | sha256 (16 primeiros) | diferença sobre a base |
|---|---|---|
| claudio-m14-e1m1-pistol-allobj-eye48-u1-h40.bin | 3b9a9da7a2b9a0fe | pistola, todos os objetos |
| claudio-m14-e1m1-pistol-swfix-eye48-u1-h40.bin | 3af987e97f0ef5bc | + botão de saída (divisão de paredes) |
| claudio-m14-e1m1-grates-eye48-u1-h40.bin | f823522153f87a18 | + grades (sprites + colisão varrida) |
| claudio-m14-e1m1-full-vdpsafe-monsters-h40.bin | 9569feaf7fd062ea | + monstros parados + `MANIFOLD_VDP_SAFE=1` (pisca no BlastEm) |
| claudio-m14-NOHUD-A-sem-vdpsafe.bin | 0d43c324384f4f7e | `MANIFOLD_NOHUD=1`, sem vdpsafe |
| claudio-m14-NOHUD-B-vdpsafe-ceu.bin | 281c517739d940c5 | `MANIFOLD_NOHUD=1 MANIFOLD_VDP_SAFE=1` |

As ROMs NOHUD (e as seguintes) têm nome no cabeçalho e tela de abertura com START/15 s.
| claudio-m14-e1m1-VBLANK-SAFE-h40.bin | ver MAME/ROM | base + grades + monstros + `MANIFOLD_VDP_SAFE=2` (escritas VDP do thread principal só durante o VBlank, onde o H-Int não dispara; sem máscara na área ativa). Soak MAME 36000 quadros limpo, FPS 3,4. BlastEm: a confirmar |

## ROMs de passeio (walk): E1M1, E1M2, E1M4, E1M5, E1M9 (12/11)
Uma ROM por fase (um menu único não cabe: texturas de cada fase ~1 MB, ROM máx. 4 MB). Base VBLANK-SAFE + `MANIFOLD_FALL=1 MANIFOLD_FALL_FAST=1` (snap de degraus e queda acelerada 12/+6/teto 96). Fases ≠ E1M1: portas abertas estaticamente (`MANIFOLD_DOORS=0`), decorações cortadas a ≤126 (monstros primeiro, depois desbaste uniforme), sem grades. E1M4 usa `MANIFOLD_SKY_MERGE=0`; E1M4/E1M5 `MANIFOLD_MAX_CELL_WALLS=24`. Receita: `tools/m14/buildwalk.sh E1M2 MANIFOLD_SPLIT_LINES=0 [...]`.
