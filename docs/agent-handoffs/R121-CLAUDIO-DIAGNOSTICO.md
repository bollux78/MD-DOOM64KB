# R121: diagnóstico do falso +167% da R120 e plano para o mínimo do E1M7 (Cláudio para o Werk)

**Branch:** `exp-claudio-r121-e1m7-20261103`, a partir de `exp-chatgpt-r120-sight-collision-20261103`.
**Estado:** código pronto, **não executado**. O Werk dispara. O workflow **não compila**: ele usa as ROMs privadas da run 41726158554, em `/home/dan/Projetos/Personal/r120-sight-collision/run-41726158554-1/`.

## 1. Causa do "+167%" (demonstrada com os próprios artefatos da run 41726158554)
Nas demos 3, 7 e 9, as rodadas do **controle** rodaram com o 68000 do BlastEm **exatamente 7× mais rápido**. Os candidatos estavam certos.

| Demo | VBlanks até o tic 151 (controle / sight) | VBlanks no trecho com render (controle / sight / both) | Razão |
|---|---|---|---|
| 3 | 137 / 946 | 551 / 3.855 / 3.857 | 6,91 e 7,00 |
| 7 | 169 / 1.170 | 526 / 3.667 / 3.669 | 6,92 e 6,97 |
| 9 | 176 / 1.220 | 527 / 3.625 / 3.630 | 6,93 e 6,88 |
| 10 (rodou depois) | 732 / 734 | 4.111 / 4.116 / 4.118 | 1,00 |

- A razão é a mesma (7) na fase só de lógica e na fase com render, e o leveltime é idêntico tic a tic. Ou seja, **o mesmo trabalho com outro relógio**, não código mais lento.
- 7 é o divisor do 68000 no BlastEm (`clocks.m68k_divider`, padrão 7). Com divisor 1, o clock fica 53,7 MHz, 7×. O teste do usuário a 13 MHz corresponde ao divisor 4.
- **Conclusão:** as três primeiras rodadas do controle leram uma configuração do BlastEm com o 68000 em overclock máximo. É a configuração do usuário, compartilhada pelo runner (`~/.config/blastem/blastem.cfg`). A seguinte já voltou a 7.
- O workflow R121 imprime a data e o `m68k_divider` desse arquivo para confirmar.
- **O falso +167% era o controle acelerado, não regressão dos candidatos.** Refeita a conta só com a demo 10 (válida): sight +0,12%, collision +0,02%, both +0,17%. Isso bate com o benchmark completo do usuário (R120 both 0,14% pior).

**Correções:**
- **Configuração fixa:** o workflow R121 roda o BlastEm com `HOME`/`XDG_CONFIG_HOME` temporários e uma cópia do `default.cfg` (ou da configuração do usuário) com `m68k_divider` forçado em 7. Recomendo o mesmo em **todos** os workflows daqui para frente: as rodadas do usuário no BlastEm não podem mais afetar o runner.
- **`r118_ab.py` estrito.** Ele recusa (rc 1, `INVALID`):
  - status diferente de `frame_limit`/`demo_end`;
  - menos de 50 tics em comum;
  - leveltime diferente do controle em qualquer tic;
  - carga dentro do trecho (leveltime descontínuo);
  - velocidade do emulador diferente: `boot_vb` (VBlanks até o primeiro G_Ticker) fora de ±5% do controle, ou fase só de lógica fora de ±25%.

  Para perfis antigos, o VB do primeiro tic comum precisa estar a ±25%.
- **Testado nos artefatos da R120:** demos 3, 7 e 9 dão `INVALID` com "emulator speed?", a demo 10 passa.
- **`r117_profile.py`:**
  - grava `boot_vb` e `skip_end_vb`;
  - **não descarta mais quadros longos como se fossem carga**: carga agora é só leveltime descontínuo. Antes, todo quadro ≥ 60 VB era tratado como carga, e isso **escondia justamente os picos**.

## 2. O que já aparece sobre o mínimo do E1M7
No `frames.tsv` da R120 (base R119 both, demo 7), **um único quadro no tic 296 custa 60 VBlanks** (1 s). Os vizinhos custam de 22 a 33. O leveltime é contínuo, então **não é carga**: é um **pico de ~0,6 s de CPU dentro de um quadro**.

- Com a janela de 1 s em grade fixa, esse quadro sozinho já dá **1,0 FPS**: é o "MIN AT E1M7 TIC 296" da R118.
- O "1,5 FPS no tic 425" da R119 provavelmente é a mesma família de picos, com outra fase da grade. Basta o tempo total mudar um pouco para o pico cair numa janela com mais quadros.
- **Portanto, o mínimo é dominado por picos de um quadro, não por um trecho uniformemente lento.** O alvo certo é **o que acontece nesses quadros**, e é isso que o R121 mede.

## 3. O workflow `r121-claudio-e1m7.yml`
1. Preflight e sha256 das ROMs privadas R120.
2. Configuração fixa do BlastEm (divisor 7), e registro da configuração do usuário (data e divisor).
3. **A/A:** R119 both, E1M7, render a partir do tic 150, em dois processos. O `frames.tsv` tem que ser idêntico e o A/B estrito tem que dar 0,00%.
4. **R120 refeita** com a configuração fixa e o A/B estrito (4 variantes × demos 3, 7, 9 e 10). O esperado é tudo válido e perto de 0%.
5. **Perfil profundo da R119 both:**
   - E1M7 só lógica;
   - E1M7 com render a partir dos tics 150, 270 e 400 (cobre 296 e 425);
   - E1M3 a partir do tic 270.

   Cada `PROFILE.json` traz:
   - `worst_windows_detail`: até 10 janelas de 1 s **sem sobreposição**, com categorias e funções;
   - `spike_frames`: quadros ≥ max(40, 2× mediana) com as funções amostradas **dentro do intervalo de VBlanks daquele quadro**, incluindo quem chamou `__mulsi3`, `R23_Map*` etc.
6. **PCs quentes no disassembly** (`r121_hotpcs.py`, só código): as 10 funções mais quentes do E1M7 com render, do E1M7 só lógica e do E1M3, cada instrução com sua contagem de amostras.
7. **Upload** só de relatórios: `PROFILE.json`, `frames.tsv`, `samples.tsv` (PCs), os `HOTPCS-*.txt` e o A/B estrito. **Nada de ROM, ELF ou demo.**

**Como disparar:**
```fish
git fetch origin; git checkout exp-claudio-r121-e1m7-20261103
date -u > .github/triggers/r121-claudio-e1m7.trigger
git add .github/triggers/r121-claudio-e1m7.trigger; and git commit -m "R121: trigger E1M7 diagnosis"; and git push
```

**O que me trazer:** todas as notas `R121 …` (A/A, R120 strict, user BlastEm config, perfis, HOTPCS) e o artefato `r121-e1m7-reports`.

## 4. Próximo passo (depois deste resultado)
Com os picos e os PCs quentes em mãos, proponho 2–3 mudanças locais com hipótese verificável, uma por variante, contra a R119 both, com os mesmos portões:
- logic fingerprint 10/10;
- pixels Off/On idênticos;
- `.data`/`.bss` iguais;
- smoke do PLAY;
- A/B estrito com a configuração fixa;
- árbitro final: o Run All no PLAY.

Hipóteses já candidatas, a confirmar pelos picos:
- (a) **`P_NoiseAlert` → `P_RecursiveSound`:** o primeiro tiro numa área grande inunda todos os setores, lendo as linhas na SRAM;
- (b) **despertar em massa** (`A_Look`/visão de muitos monstros no mesmo tic);
- (c) **`P_CheckSight`** com SRAM por seg.

Nada será proposto sem o pico apontar para a rotina. Se não houver mudança exata com ganho material nos picos, recomendo parar e manter a R119 both como final.
