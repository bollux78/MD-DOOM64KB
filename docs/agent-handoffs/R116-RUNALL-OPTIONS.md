# R116 — Benchmark direto, Run All Demos in Sequence e Options

**Branch:** `exp-chatgpt-r116-demo-sequence-20261102` (experimental, não mesclada). **ROMs e demos privadas:** nunca publicar em artifacts/Git.

## Interface do usuário (ROM PLAY)

Menu principal > **Benchmark** abre **diretamente** a lista:
1. **Run All Demos in Sequence**
2. E1M1 UV-Max
3. E1M2 UV-Max
4. E1M3 UV-Max
5. E1M4 UV-Max
6. E1M5 UV-Max
7. E1M6 UV-Max no cap
8. E1M7 UV-Max
9. E1M8 UV-Max
10. E1M9 UV-Max
11. E1M6 Special cap

Os antigos E1M1/E1M7 baseados em DEMO3 saíram das **opções do menu**; o DEMO3 permanece internamente como entrada do mecanismo de benchmark e no fluxo legado, onde exigido.

## Opções do usuário

O Run All NÃO altera **H32/H40, recorte horizontal ou vertical, paleta, Shadow ON/OFF nem IA Normal/Low**. A imposição de IA Normal que existia no primeiro pacote R116 foi removida. `G_ReloadDefaults()` só limpa flags de demo, não altera Options. O result-screen usa H40 para mostrar texto ao terminar, como o benchmark anterior.

## Funcionamento

- Seleção Run All ativa `r116_seq_on=1` e carrega a primeira demo. `r116_sel=1..10`.
- Ao fim de cada demo (marcador ou saída do mapa), `G_CheckDemoStatus` contabiliza o menor espaço livre de zone e agenda a seguinte.
- A troca de demo/nível ocorre em `R116_SequenceContinue` **após G_Ticker ter retornado**, dentro do loop externo. `r116_seq_pending` impede processamento duplicado do mesmo término.
- Os contadores de FPS são reiniciados apenas no início da primeira demo; as dez usam **contagem global de quadros / tempo de VBlank**, com mínima/máxima por janelas de 1 segundo. Inclui custos de transições e carregamento, não é a média simples dos 10 FPS.
- Ao final da décima demo, a tela apresenta FPS, total de quadros, segundos e mínimos de zone global; START volta ao menu.
- Cada demo individual continua exibindo seus próprios resultados.
- Demos são **inputs reproduzíveis para teste de segurança**, não garantia de sincronia ou fidelidade ao Doom PC.

## Validações verificadas

- [Build 41567872714](https://github.com/bollux78/MD-DOOM64KB/actions/runs/41567872714): build PL/PF, limites ROM/BSS, stress BlastEm por mapa e smoke de boot PLAY aprovados.
- [Teste de transição 41568242897](https://github.com/bollux78/MD-DOOM64KB/actions/runs/41568242897): **PASS_TRANSITION**. Para caber em 10.000 quadros, a sonda ativou modo sequência no PERF, forçou um fim controlado em E1M8 e confirmou E1M9 ativa, `r116_seq_completed=8`, `r116_seq_pending=0` e IA Normal mantida (`r89_ai_low=0`).
- A validação específica foi incorporada ao workflow principal como porta adicional de CI para builds subsequentes.
- BSS: 57.884 bytes PL (36 de margem); 57.880 bytes PF (40 de margem). ROM 3.932.160 bytes cada.

**Ainda não verificado:** percorrer todas as dez demos com vídeo habilitado até o resultado final, incluindo cada combinação de Options, e teste no Mega Drive físico. O resultado positivo da sonda prova a troca segura de uma demo para a seguinte, não toda a sequência completa.

### ROM para teste manual

`/home/dan/Projetos/Personal/r116-demotest/run-41567872714-1/doom-md-r60-r116-demotest-pl.bin`

Use o BlastEm primeiro; E1M6 UV no runner ainda mostrou maior bloco livre de apenas 576 bytes, merecendo atenção antes de rodar o stress máximo no Mega Drive físico.
