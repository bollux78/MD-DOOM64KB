# Handoff para o Werk — estado atual da D01 e próximos testes

Branch `exp-dread-md-d01-claudio`. Build de referência: commit `0681cb0`, run GitHub Actions `44930721164` (ROM em `dread-md-episodio.zip`). Este handoff substitui o resumo de desempenho dos handoffs anteriores. Os handoffs de SRAM (`HANDOFF-WERK-SRAM.md`) e de linhas/colunas (`HANDOFF-WERK-LINHAS-COLUNAS.md`) continuam valendo, com as ressalvas abaixo.

## 1. O que mudou desde o último handoff

- **Modo linhas, pulos:** corrigidos pela tabela `hint_tab` no `hint_b` (sem desvio, uma leitura do contador). Confirme no console.
- **Modo colunas, tela preta:** corrigido religando a tela em `set_mode()`. Confirme nas quatro combinações: H40/H32 × linhas/colunas, entrando e saindo da pausa.
- **Laço de colunas, primeira etapa (c9aa748):** cada coluna tem um registro de 12 bytes lido com `movem`; a textura começa sem multiplicação no caso comum (`tex_fast`); o escalonador é chamado por salto direto.

## 2. Números de referência (Genesis Plus GX, sem SRAM, modo linhas)

| Cena | Antes | Agora |
|---|---|---|
| Benchmark E1M1 (312 quadros) | 3,44 FPS | **3,73 FPS** |
| Começo de E1M1, girando (LIVRE, ~1500 quadros) | 6,15 FPS | **6,39 FPS** |
| Começo de E1M2, girando 300 quadros (mesma medida do SRAM) | ~4,8 FPS | a medir |

Referência do Ferret, Alpha 2, mesma cena: 7,77 FPS com SRAM de 16 bits; ~4,7 sem SRAM (medido pelo Werk).

A imagem do benchmark deve sair **idêntica pixel a pixel** à do run 44922171487 (commit `d4f9f4b`) e à do run `44930721164`. Se não sair, avise antes de medir FPS.

## 3. Testes a fazer (nesta ordem)

1. **Build e artefato:** confirme que o run `44930721164` (ou um mais novo) passa no CI e entregue o zip em `/home/dan/Projetos/Personal/dread-md/` com o link do artefato.
2. **Correções no console (pelo menos no emulador):** pulos no modo linhas e tela preta no modo colunas, nas quatro combinações de modo, com entrada e saída da pausa.
3. **Benchmark:** rode E1M1 (312 quadros) e anote FPS e se a imagem bate com a referência.
4. **Spin no começo de E1M1:** LIMITE LIVRE, ~1500 quadros, parado e girando. Anote FPS e a média.
5. **SRAM de 16 bits, teste A** (ver `HANDOFF-WERK-SRAM.md`): só se a ROM de teste tiver menos de 2 MB. Meça com e sem SRAM nos dois modos. Essa medição é a que decide se vale o segundo framebuffer no modo colunas.

## 4. Coisas que não mudam

- O jogo tem que rodar sem SRAM. A SRAM só entra com teste de presença de 16 bits.
- Sem mapper ou SSF na versão principal.
- Não publicar WAD nem ELF.
- Toda ROM de teste: nome no cabeçalho, tela de título com o que ela testa e "aperte START ou aguarde 15 segundos", e jogável.

## 5. Pendências conhecidas

- **BlastEm:** o benchmark termina com "BlastEm RSP EOF" desde o commit de correção de glitch. O gpgx funciona. Se o BlastEm também travar no seu teste, anote o quadro e o commit.
- **Laço de colunas, segunda etapa (em andamento):** reescrita no formato de registradores e lista sequencial, ainda não entregue. Não meça esta etapa como resultado final; o build atual é a referência.
- **Lista de paredes por subsetor (BSP):** ainda não feita. A BSP e a projeção somam ~27% do tempo.

## 6. O que devolver

- Commit ou run usado, com o link do artefato.
- FPS de cada cena, com a configuração (SRAM sim/não, linhas/colunas).
- Se o benchmark mudou de imagem, o frame e a diferença observada.
- Vídeo curto do teste de console, se houver glitch.
