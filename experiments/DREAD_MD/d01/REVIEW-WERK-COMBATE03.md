# Revisão do Cláudio: branch `exp-dread-md-d01-werk` (Combate 03, f8476c5)

Comparado com a base `fa5339e`. Escopo pedido pelo usuário: implementação de inimigos e de mapas.

## O que está correto e bem feito
- **Estrutura de mapa (`DreadMap` + `dread_map`)**: as macros mantêm o renderer igual e a troca de mapa é um
  ponteiro. Ordem certa no `main`: `dread_map` → `R_Init` → `Actors_Init` → portas.
- **Setores em 16 bits** (`NO_MAP_SECTOR`), verificações de limites no conv (setores, 255 texturas, 4096 subsetores).
- **Deduplicação de colunas de textura** com tabela de ponteiros por textura; o asm (`tex_part`) foi adaptado
  corretamente (`lsl.w #2` + `movea.l`), e o formato "coluna guardada duas vezes" dos escaladores foi mantido.
- **PVS compactado por linha** (RLE de zeros) e descompactado só quando o subsetor do jogador muda: barato e certo.
- **Cache de vértices com hash** para mapas com mais de 2730 vértices: economiza RAM sem quebrar o caso pequeno.
- **Atores em RAM com lista por subsetor**, desenhados pelo mesmo esquema de janela do D01 (recorte correto
  mesmo com movimento). Religação de lista ao trocar de subsetor está certa.
- IA em 4 grupos com `dt` acumulado por grupo: correto e barato quando não há combate.
- Build falha se a ROM passar de 4 MiB.

## Problemas e melhorias (por prioridade)

### 1. Linha de visão cara (vai derrubar o FPS em combate)
`visible()` usa `int32 × int32` e divisão de 32 bits: compilado para 68000, cada linha testada chama
**8 × `__mulsi3`** e cada passo do raio **2 × `__divsi3`**. Um teste de 512 unidades custa da ordem de
50–100 mil ciclos (quase um VBlank inteiro). É chamado ao acordar, a cada ataque e para cada candidato do tiro.
O bench fixo não passa por combate, por isso "IA ligada = IA desligada" (3,80 × 3,79 FPS) não mede isso.
Correções:
- **Usar a tabela REJECT do WAD** (setor × setor, 1 bit; é o que o Doom faz antes de qualquer traçado): se o bit
  diz "não vê", nem traça. Exportar no conv (E1M1 ≈ 1 KB).
- Coordenadas cabem em 16 bits dentro de 1024 unidades: produtos cruzados com `muls.w` (helper `muls16`).
- Andar pela grade com DDA (Bresenham de células), sem divisão por passo; testar cada linha uma vez por chamada.
- Limitar: no máximo N testes de visão por quadro (fila), como o Doom faz por tic.

### 2. Paleta do episódio ajustada só com a E1M1
`build_map.sh` gera a paleta convertendo a E1M1 e aplica a mesma às outras oito. Texturas e sprites que só
existem em E1M2–E1M9 (outras cores, sargento etc.) ficam com pares ruins. Fazer o ajuste da paleta com os
itens (texturas, flats, sprites, céu) **de todos os mapas juntos**: uma passada que só coleta as cores
(`--collect-items`), um ajuste único, depois a conversão com `--palette`.

### 3. Modo colunas sumiu no episódio (`DREAD_ROW_ONLY`)
É uma regressão de uma função que o usuário pediu (troca em tempo real H40/H32 × linhas/colunas).
Não precisa voltar a cópia em words das texturas (que dobra a ROM): gerar um **segundo conjunto de escaladores
que lê byte e escreve os dois bytes** (`move.b d16(a1),d16(a0)` + `move.b d16(a1),d16+1(a0)`, 12 bytes e
32 ciclos por linha; ~220 KB de ROM para 128 níveis × 144 linhas), e um `tmk` igual. Fills já funcionam.
Alternativa mais barata em ROM: 64 níveis só para o modo colunas.

### 4. Monstros mortos desaparecem
`if (actors[id].hp) project_thing(...)`: o cadáver some. No Doom o corpo fica (último frame da morte).
Trocar o sprite pelo frame de morte (conv já tem `PLAYW`/`PLAYN`; exportar `POSSL`, `TROOM` etc.) e não
desenhar só enquanto toca a animação.

### 5. Comportamento dos monstros (diferenças do Doom)
- **HP e dano fixos** (30 para todos, pistola 10): no Doom zombie 20, imp 60, sargento 30, demônio 150;
  pistola 5×(1..3). Fazer uma tabela por tipo no conv (`MapThing.flags` → tipo).
- **Acordar só por visão a ≤ 512 unidades**: o Doom acorda também por **som** (tiro do jogador se propaga pelos
  setores conectados, parando em linhas "block sound"). Pré-calcular adjacência de setores no conv e acordar
  todos os atores dos setores alcançados quando o jogador atira.
- **Ataque só a ≤ 176 unidades, 5 de dano fixo a cada 60 VBlanks**: zombie/sargento atiram (hitscan) de
  qualquer distância com visão e chance de errar; imp arremessa bola de fogo (projétil) e arranha de perto.
- **Movimento em linha reta com `continue` ao bater**: o monstro trava em quinas. Usar o `P_NewChaseDir` do Doom
  (8 direções, tenta a direção direta, depois alternativas e aleatória, com `movecount`).
- Sem colisão entre atores (podem se sobrepor) e sem altura (podem "subir" degraus de até 24 sem checar teto do
  destino com a altura do monstro — já checa `ceil - floor < 56`, ok para o jogador; monstros variam).
- Tiro do jogador: cone fixo de ±16 unidades laterais; o Doom usa autoaim por ângulo (mais tolerante de longe).

### 6. Só a frente dos monstros (rotação 1, frame A)
Pendente e conhecido. Com o espelhamento das rotações 6–8 a partir de 2–4 (inverter as colunas no runtime), o
custo de ROM cai à metade.

### 7. ROM perto do limite (3,75 MiB de 4)
Com rotações, animações, SFX e o modo colunas não cabe. Ganhos possíveis: buckets de luz 4 → 3 (−25% das
texturas), deduplicar sprites por bucket quando idênticos, comprimir o PVS mais (bits por bloco de 8×8),
músicas XGM2 só das fases incluídas.

### 8. Pequenos
- `HANDOFF-CLAUDIO.md` e o ZIP da ROM no git: ok pelas regras (shareware), mas binários no histórico deixam o
  repositório pesado; preferir o artefato do CI.
- Morte do jogador volta a 100 de vida (placeholder) — ok por enquanto.

## Ordem sugerida
1 (visão barata + REJECT) → 5 (HP/dano/som/chase) → 4 (cadáver) → 6 (rotações/animação) → 2 (paleta do
episódio) → 3 (modo colunas) → transições de fase. Medir combate com um bench novo que passe por uma sala com
monstros (ex.: E1M1 sala do zigue-zague), não só a rota atual.
