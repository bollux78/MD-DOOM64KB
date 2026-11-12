# Pedido ao Werk — ROMs de cada família M0..M14 em `projetos/manifold-doom/roms/`

De: Claudio (Claude) · Para: Werk · Data: 2026-11-12 · Pedido do usuário (Diego): ter no runner local uma ROM de cada família do Manifold, de M0 a M14, guardadas e identificadas, para comparação lado a lado no BlastEm/console.

## Destino e organização (no runner do usuário)

```
projetos/manifold-doom/roms/
  M00/ ... M14/            # uma pasta por família
    <nome>.bin             # ROM final
    <nome>.build.txt       # commit, branch, comando/workflow, variáveis MANIFOLD_*, data, quem compilou
  MANIFEST.sha256          # sha256 de todas as ROMs
  MANIFEST.md              # tabela: família | arquivo | commit | branch | flags | status (OK / NAO REPRODUZIDA + motivo)
```
Nome do arquivo: `werk-mNN-<descricao-curta>-h40.bin` (ou h32 quando for o caso). Não sobrescrever: ROM nova da mesma família = novo nome.

## Regras obrigatórias (valem para todas)
1. Cada ROM precisa ser jogável: START entra no jogo (ROMs de teste de câmera/autowalk contam como a própria finalidade, mas devem abrir sem erro).
2. Identidade: nome/finalidade no cabeçalho da ROM (aparece na janela do BlastEm) e tela inicial preta com fonte padrão SGDK: nome, o que testa e "PRESS START OR WAIT 15 SECONDS". Isso já existe no `stage_rom.py` do branch `exp-manifold-m14-e1m1` (`m14_identity`, variáveis `MANIFOLD_ROM_NAME` e `MANIFOLD_ROM_TEST`). Sem acentos nem `?` nesses textos. Famílias antigas: se o stage_rom.py da época não tem isso, compile com o do M14 só se o resultado ficar equivalente; senão compile no commit original e registre "sem identidade" no MANIFEST.
3. Honestidade: se uma família não for reproduzível (commit sem receita clara, workflow removido, build falha), NÃO improvisar. Registrar como `NAO REPRODUZIDA` com o motivo e seguir.
4. Cada build: validar que arranca (BlastEm headless ou MAME) e registrar `build: PASS/FAIL` e `boot: PASS/FAIL`.

## Receita de build
- Base atual (M14): `experiments/DOOM_Manifold_E1M1/tools/m14/build_local.sh NOME VARIAVEIS...` (branch `exp-manifold-m14-e1m1`). Saída: `out/release/rom.bin`. Requer o Manifold upstream fixado em `b6fe52a`, o WAD shareware e o SGDK local do runner (ajustar os caminhos do script ao runner).
- Famílias antigas: workflows `.github/workflows/manifold-e1m1-m01.yml`, `manifold-e1m1-rom.yml`, `manifold-console-set.yml` (M12, `builder: werk`), `manifold-m13-werk-hud.yml`, `manifold-e1m1-diagnostic.yml`. Usar `git checkout <commit>` do último commit da família.

## Mapa das famílias (commit-âncora = último commit da família no histórico do branch `exp-manifold-m14-e1m1`; confirme com `git log --grep`)

| Família | O que é | Âncora / pista | Observação |
|---|---|---|---|
| M00 | Controle: Manifold upstream sem Doom (mapas de teste do próprio Manifold) | upstream `ehaliewicz/Manifold` @ `b6fe52a` | Meu entendimento; M0 não tem commit próprio. Se o usuário/Werk definiu outra coisa para M0, registrar |
| M01 | Primeira geometria E1M1 como células/portais, estrutural | branch `exp-manifold-e1m1-m01`, workflow `manifold-e1m1-m01.yml` | README diz que a primeira ROM não passou no build; pode não haver ROM jogável |
| M02 | Jogável, sem ADDRESS ERROR; andar/girar (~6-12 fps) | `b281951` (autowalk) / `79bc0ca` | |
| M03 | Células convexas exatas, fog, ROM tour de câmera | `3f1f648` | |
| M04 | Texturas Doom, paleta 16 cores, céu SKY1 | `28ae618` | |
| M05 | VRAM reclamada, céu largura total, degraus texturizados | `59e0c21` | |
| M06 | Céu/fog, arma 2x128 tiles | `0cf6b10` (handoff `MANIFOLD-E1M1-M06-*.md`) | |
| M07 | Olho da câmera 82→64 | `91551fc` | Sem build próprio documentado; provável variante do M06/M08 |
| M08 | Portas temporárias, câmera baixa, perfil de escadas | `f437653` / `45ee878` | LOD de parede distante foi rejeitado; usar versão validada |
| M09 | (sem commits marcados) | — | Provavelmente NAO REPRODUZIDA; verificar histórico/handoffs |
| M10 | HUD clássico do Doom (R128 HUD-WAD), ROMs pareadas control/doom | `5bde241` | |
| M11 | Near-plane LUT, XGM/música, HUD/arma isolados | `2920280`; branches `exp-manifold-m11-music`, `exp-manifold-m11-nearclip-hud` | |
| M12 | Variantes claudio-m12 (play/control/autowalk H40), objetos | `0dc3e92`; branches `exp-manifold-m12-*`; `manifold-console-set.yml` | Várias ROMs; guardar ao menos play-h40 e control-h40 |
| M13 | Auditoria de engine, HUD CRT (Werk), M13.2 sky-merge/all-leaves/near-safe | `e99f64c`; `manifold-m13-werk-hud.yml` | Guardar a ROM que o usuário usou como base (H40 sky-merge + near-safe) |
| M14 | Base atual: BSP=0, objetos, portas, pickups, eye48, tex u1, pistola, grades, monstros parados, identidade | `e324839` (HEAD do branch) | Receita e flags em `docs/agent-handoffs/MANIFOLD-M14-ROMS.md`. ROMs de ref.: `...grates-eye48-u1-h40`, `NOHUD-A-sem-vdpsafe`, `NOHUD-B-vdpsafe-ceu`, `full-vdpsafe-monsters-h40` |

## Entregáveis
1. ROMs + `.build.txt` nas pastas M00..M14.
2. `MANIFEST.sha256` e `MANIFEST.md` (com status por família, inclusive as não reproduzidas).
3. Um commit/nota curta no repo (`docs/agent-handoffs/`) com o resultado e o caminho final dos arquivos. ROMs binárias NÃO vão para o GitHub (política do repo); ficam só no runner.
4. Se uma família for ambígua, escolher o commit mais próximo do que o usuário testou e anotar a dúvida em vez de parar.

## Fora de escopo
Não alterar renderer nem corrigir defeitos; só compilar, identificar, validar boot e guardar. Dúvidas sobre o motor M14: perguntar ao Claudio.
