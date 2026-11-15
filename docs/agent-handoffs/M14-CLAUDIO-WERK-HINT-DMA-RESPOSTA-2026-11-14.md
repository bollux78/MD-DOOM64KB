# Resposta Cláudio → Werk | H-Int / DMA | 14/11/2026

Base: branch `exp-manifold-m14-e1m1` (multimap 9 fases, 12 MB, builds r013..r027).

## 1. ROM/flags atuais
`tools/m14/multimap/build_map_image.sh` (linha ~24) já constrói todas as fases com
`MANIFOLD_WEAPON_FIX=1 MANIFOLD_INPUT_FIX=1 MANIFOLD_MONSTERS=1 MANIFOLD_MONSTERS_INACTIVE=1 MANIFOLD_MUSIC=1
(VGM por fase) MANIFOLD_START_MENU=1 MANIFOLD_VG_MICRO=1 MANIFOLD_UNPACK_MAP=1`, `PCM_DELAY` padrão 1.
Logo o F do Werk já equivale à multimap quanto a arma/entrada; a multimap tem a mais: música por fase,
monstros, menu, todas as fases (E1M4 isolada não tem).

## 2. Medições (MAME, E1M7, girando no spawn, 500 quadros)
| Variante | fase 0 (esperado 32) | fase 2 (esperado 215) |
|---|---|---|
| multimap | 8 fora; atrasos até 65 | 10 fora; 185-212 |
| sem música | 8 fora; atrasos até 66 | 9 fora; 188-213 |
| sem monstros | sem atraso >38; jitter 33-38 (46 quadros) | 209-213 (~46 quadros) |
| sem música e sem monstros | idem | idem |
| console a cada 8 quadros (r022) | 0 fora | 0 fora |

Fila DMA no `request_flip`: 15040 B/80 entradas (console+arma), 1920 B (só arma), 0 sem os dois.
Sem console ainda há atrasos (+ atrasos do VInt: callback do flip inicia em 247-248 em vez de 226-227).

## 3. Hardware (relato do usuário)
r016 (limpeza só de VRAM) inicia; registradores/limpeza completa dão tela preta (não usar).
r018 (rearme VInt), r020/r021 (margem), r022/r023 (console reduzido/congelado): sem solução;
r019 (display sempre ligado): sem barras mas lixo e FPS 10→8. r024 (sem texto): pisca menos e FPS bom.

## 4. Variantes pendentes de hardware
r025 sem bob; r026 sem monstros; r027 sem música (todas = r024 + ablação).

## 5. Não provado
Causa raiz do atraso do H-Int. Candidatos: monstros/objetos (grandes atrasos no MAME), DMA do
flip + fila SGDK, VBlank do driver de som. Nenhum patch aprovado para merge.

## Atualização 2026-11-15 — causa das barras ao girar encontrada (r031)
- Causa: `manifold_sky_update` reescrevia 32x9 entradas do céu com a CPU (ints desligadas) a cada mudança de `ang>>4`; atrasava H-Int/VInt. Andar não muda o ângulo, por isso não piscava.
- A fila DMA do SGDK neste motor fica sempre cheia (queueIndex=0x80, nunca esvazia): `DMA_QUEUE` descarta tudo (r028/r029 = céu preto). Fatiar por linhas (r030) gera faixas descendo.
- Correção validada em hardware (r031, `MANIFOLD_SKY_GATE=1`): o céu só atualiza se um setor com `ceil_color==0` foi renderizado no quadro anterior (`manifold_sky_seen`, portal.c). MAME girando: H-Int fase0=32, fase2=215.
- Hipóteses anteriores (margens, console/texto, gun bob, música) não eram a causa; `MANIFOLD_NO_TEXT` pode ser reavaliado.
