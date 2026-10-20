# R46 — composição visual flexível (céu / arma / HUD), decisão após M2/M3

**Decisão do usuário:** o céu **não precisa** usar o plano B. Se o céu consumir muitos tiles ou reduzir desempenho, **arma e HUD podem usar o plano B**. Nenhum componente tem hardware fixo nesta etapa. Priorizar melhor visual versus VRAM, CRAM e custo de upload real.

## Alternativas a comparar, sem assumir vencedora

| Variante | Plano A | Plano B | Sprites de hardware | Condição |
|---|---|---|---|---|
| S0 — baseline | Mundo 3D + céu + arma pelo software; HUD usual | Sem uso separado | Nenhum novo | Referência visual/FPS R45/R44 |
| S1 — céu em B | Mundo 3D com janelas transparentes onde céu é visível | Céu panorâmico com scroll por ângulo | Arma, se viável | Requer transparência correta e realocação de tile banks |
| S2 — arma/HUD em B | Mundo 3D com céu por software | Arma/HUD, composição e deslocamento controlado | Opcional para efeitos | Separação por transparência/prioridade; avaliar se o plano serve a imagens móveis sem atualizar mapa/padrões demais |
| S3 — arma em sprites | Mundo 3D + céu por software | Opcional/nenhum | Arma em múltiplos sprites | Respeitar quantidade por linha, VRAM, paleta e sprites usados por outros objetos |

**Nota técnica:** plano B é um tilemap que permite scrolling; não oferece por si só deslocamento e transparência de objeto como sprites. A arma exige mascaramento por padrões, prioridades e, possivelmente, atualizações parciais; portanto S2 não é automaticamente melhor ou mais fácil que S3.

## Restrições reais do código atual

- R22 P4 trabalha em 76×44 amostras, 2 bancos de padrões, bloco de 32 bytes por tile, frames `1672 B`; o módulo M1B gera map rows sem segundo `r22_map` de 1596 bytes.
- O código standalone R22 configura BGA/BGB na mesma região de VRAM `0xE000`; antes de usar B como céu ou HUD, M3 deverá separar posições e gerir as transferências.
- Os padrões dinâmicos do banco 0 (54–851) e 1 (890–1687), junto da fonte a partir de 1696, deixam pouco espaço para novos gráficos persistentes no mesmo layout. O 8×8 R39f usa tiles 16–241, que se sobrepõem parcialmente ao banco 0. A transição 8×8↔4×4 exige recarregamento.
- O céu pode permanecer por software com scroll angular atual: a otimização visual pode vir da arma/HUD, sem tocar no cielo.
- Paleta original do 4×4 como padrão; variante global cinza R43/R45 é opcional. Desejo futuro de cinza só em chão/teto, paredes coloridas como antes.
- O HUD 38×22 da intermissão foi corrigido na R44 e **não pode regredir** ao reorganizar planos e camadas.

## Critérios objetivos para escolher

1. **ROM e VRAM**: bytes de padrões céu/arma/HUD, tilemap, buffers, glyphs, SRAM; mudanças de banco e largura de DMA.
2. **CRAM**: alocação das quatro paletas durante 8×8 R39f (quatro ocupadas) e 4×4; não prometer mais de 4×16 cores físicas.
3. **SFX/música**: manter XGM2/PCM, sem bloqueios longos do barramento Z80.
4. **Perf e latência**: FPS DEMO3 2134 frames, carga por VBlank e animações da arma. Não assumir 60fps se frames de sprite só forem atualizados por tick do jogo.
5. **Cena de teste**: E1M1 exterior/céu e sala interna, uma arma em idle/fire/pickup, HUD e E1M1→E1M2, CRT real e BlastEm.
6. **Integração dual**: plano escolhido deve coexistir com modo 8×8, opção Off/Checker/Vertical e preservar estado do jogo na troca.

**Não há implementação dos protótipos S1–S3 na M2B.** Ela trata dos limites verticais e prepara a geometria 76×44. Decisão visual somente depois do M3/VDP e dos testes comparativos.
