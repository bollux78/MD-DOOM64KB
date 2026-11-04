# R127: diagnóstico do pior momento da R126b (E1M1, tic 237) (Cláudio para o Werk)

**Branch:** `exp-claudio-r121-e1m7-20261103`. **Não compila:** usa as ROMs privadas da run 41882892479 (R126b), em `/home/dan/Projetos/Personal/r126-claudio-early/run-41882892479-1/{c-control,c-early}/`.

## Contexto
No Run All, a R126b deu 5,49 FPS de média e 1,9 de mínimo (R122: 5,26 e 1,5). O pior momento passou a ser **E1M1, tic 237**. Antes era o E1M7, por causa dos picos de tiro.

## O que o workflow `r127-claudio-e1m1.yml` faz
1. Fixa a configuração do BlastEm (68000 com divisor 7).
2. Roda o perfil da demo 1 (E1M1) com `r117_profile.py`:

   | ROM | Rodada |
   |---|---|
   | R126b (`early`) | só lógica |
   | R126b (`early`) | render a partir do tic 150 |
   | R126b (`early`) | render a partir do tic 200 |
   | R122 (`control`) | render a partir do tic 200, para comparar |

   Cada `PROFILE.json` traz `spike_frames` (as funções que rodaram dentro de cada quadro de pico) e `worst_windows_detail`.
3. Mapeia os PCs quentes no disassembly da R126b em duas versões: E1M1 inteiro e **só os tics 225–250**, a janela do pico.
4. Upload só de relatórios.

**Como disparar:**
```fish
git fetch origin; git checkout exp-claudio-r121-e1m7-20261103
date -u > .github/triggers/r127-claudio-e1m1.trigger
git add .github/triggers/r127-claudio-e1m1.trigger; and git commit -m "R127: trigger E1M1 diagnosis"; and git push
```

**O que me trazer:** as notas `R127 …` (perfis com piores janelas e picos, HOTPCS) e o artefato de relatórios.

## Como vou ler
- **Pico de lógica** (porta ou elevador abrindo, som, monstros acordando): pode haver correção pontual.
- **Render puro** (vista ampla com muitas paredes e sprites): sem mudar a imagem, provavelmente não há ganho grande. Nesse caso a R126b fica como base final.
