# R53 — protocolo de validação CRT, 24 ROMs (22/10/2026)

## Estado da implementação
- Branch experimental: `r53-microdither-research`.
- Ponto inicial: R52 Cláudio, workflow verde `39764108632` (não substitui R50 ou R52).
- Gerador `scripts/lab/gen_r53_micro.py` seleciona offline um companheiro de cor para cada índice PAL0/PAL1. O índice zero permanece transparente. Companion deltaE <=38 e |Δluma|<=38 na subpaleta normal; nenhum ganho aparente obriga uma troca.
- O renderizador gera, uma vez na inicialização, dois bancos imutáveis de 256 tiles (A:256..511; B:512..767); a B usa atributo PAL1 e tile base 512. O font começa em 1440.
- Cenas 76x44 4×4, CPU microkernel, VBlank DMA e framebuffer WRAM 3344B preservados; reinicialização da cena restaura os dois bancos após artes estáticas.
- **M25:** 3 pixels da cor-base e 1 da cor companheira em cada linha, posições desencontradas; **M50:** padrão xadrez de 1×1 pixel físico (2 base/2 companheira).
- Não é mistura de PAL0 com PAL1 no mesmo sample: a seleção de paleta continua por tile/plane; microdither é *interno* a cada PAL.

## 24 combinações prontas no workflow
6 perfis de paleta × 2 dispersões espaciais × 2 modos.
Perfis: `n25f`, `n25a`, `l32f`, `l32a`, `freef`, `freea`.
Proporções: `m25` ou `m50`.
Modos: `play` (hardware/qualidade) e `perf` (DEMO3).
Nome: `doom-md-r53-<perfil>-<proporção>-<modo>.bin`, exemplo `doom-md-r53-n25f-m25-play.bin`.

## Comparação visual — mesma cena, mesma câmera
1. Capture o controle sólido R52 correspondente, M25 e M50, todos com o mesmo ângulo e iluminação em E1M1.
2. Avalie no CRT real em tamanho nativo; registre tipo de conexão (RGB/composite), overscan, fotos na mesma exposição e foco e distância.
3. Inspecione o pilar bege e cinzas, texturas metálicas, chão azul, gradas, áreas muito escuras, mão/arma, céu, luminosidade de corredores.
4. Mova-se devagar; microdither finíssimo pode criar cintilação, aliasing ou padrões de moiré invisíveis numa captura estática. Observe scrolling e tiros.
5. Confira VIDA, ARMADURA, BALAS e relógio FPS no HUD. A R52 realocou índices da PAL0; legibilidade pode variar.
6. Abra menu, New Game, intermission, reinicie; verifique que o dither continua após arte nativa. Teste flashes vermelhos e efeitos de subpaleta.
7. Em cada PERF, compare 2 runs completos de 2.134 frames DEMO3, mesma velocidade do emulador e configurações, com R52 equivalente. Registre FPS e tempo; a referência histórica R52 Cláudio foi 5,46 FPS, 390,87s.

## Interpretação
- Dither de 1px **não eleva a resolução lógica 4×4**.
- `forbid` vs `allow`: quando `allow` gera cor 0, o padrão a mantém totalmente transparente em vez de intercalar opaco no pixel 0.
- Se uma PAL base não tiver parceiro adequado sob a restrição de contraste, o tile pode continuar monocromático. Relatório `MICRO-*.json` indica número de índices realmente misturados.
- No CRT, preferir redução do banding sem moiré, preservação de cor em E1M1/E1M2 e FPS próximo de 5,46. No monitor LCD, avaliar sem filtros em paralelo.
- Escolher a melhor R53 somente após seu teste no hardware real. Não promover candidatos automaticamente por ΔE da simulação nem pelo relatório da compilação.

## Acesso
Workflow `r53-microdither-crt-matrix.yml` produz `doom-md-r53-microdither-crt-matrix` (24 ROMs + perfis, oráculos, SHA, relatório de memória).
