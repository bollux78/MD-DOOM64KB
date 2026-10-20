# R41 Q1 — Primeiro profiler separado do renderizador 4x4

Base imutável: R40b `r40b-pixel4-text-diff`. Este experimento é **independente da integração R40c** e não altera o código do renderizador limpo.

## Builds
- `doom-md-r41-control-p4perf.bin`: o caminho original R40b pixel4, MOVEP mall, DEMO3 2134 frames, sem profiler.
- `doom-md-r41-profile-p4perf.bin`: mesma base, com `-DDOOM_R41_P4_PROFILE` e amostragem de 14 estados de CPU na interrupção VBlank (60 Hz), resultados na tela. A ROM perfilada tem custo extra; FPS desta ROM NÃO substitui o baseline limpo.

## 14 buckets amostrados
0 OTHER/LOGIC; 1 FRAME SETUP; 2 BSP OTHER; 3 COLUMN OTHER; 4 MASKED; 5 VDP WAIT; 6 WALL DRAW; 7 MULTIPATCH; 8 STORE RANGE; 9 ADD LINE; 10 CHECK BBOX; 11 FLAT DRAW; 12 SPRITE/FUZZ; 13 VRAM UPLOAD.

Os estágios 1–10 seguem os R7 existentes no renderer; 11 e 12 envolvem chamadas reais de desenho 4x4; 13 abrange `R22_UploadBack` e 5 sincronização com VBlank.

**Limitação decisiva:** VBlank sampling **NÃO mede ciclos exatos**. `R22_UploadBack` bloqueia interrupções durante cada transferência para VRAM, então o bucket 13 provavelmente está SUBCONTADO. Não inferir que upload é barato de uma porcentagem pequena. Para Q3 comparar upload usar hardware trace ou instrumentação própria com HV timer calibrado.

Os 14 contadores são de 16 bits: no benchmark de 2134 quadros a ~3 fps (~42.5k VBlanks), ainda cabem sem wrap. Na execução TIMEDemo R41 são zerados em `I_BenchmarkReset()` e congelados em `I_BenchmarkShowResults()`, antes do redesenho do painel.

## Testes necessários
1. Duas ROMs devem passar em CI, ROM <=4 MiB, flag pixel4 76x44, 300 frames BlastEm, sem kernels asm 8x8.
2. Rodar os DOIS timedemos até DEMO3 2134. Controle deve reproduzir aproximadamente 3,01 FPS (R40 fast; para R40b final faltava benchmark). Não exigir FPS idêntico da versão instrumentada.
3. Foto da tela de perfil com percentuais nos 14 buckets. Somas próximas de 100%, não exatamente ciclos. Atenção às amostras mascaradas durante upload.
4. Não atribuir a P5/P6/BSP ou Q2 kernels um ganho sem benchmarks isolados; priorizar Q2/Q3 com base nos gargalos realmente capturados e mensuração alternativa de upload.

## Importante para o próximo estágio
O R22 4x4 atual NÃO usa `R20_RegColumn`: `r22_video.inc` contém `#error` contra `R20_REG_COLUMNS` e `FLAT_INLINE`. Qualquer asm Q2 futuro deve operar sobre framebuffer nibble-packed 1672 bytes, stride 38, preservando sobreposição de sprites e paleta.
