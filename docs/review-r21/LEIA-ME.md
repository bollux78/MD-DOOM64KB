# R21 — primeira leva de otimizações sobre R20h vc-all

24 ROMs, DEMO3/NTSC60Hz/2134 frames, mesma viewport38x22 e músicaE1M1.
Base: R20h vc-all, que concluiu no hardware a7,67MHz em178,80s/11,94FPS; referência BlastEm176,83s/12,07FPS. Render continua8x8 nesta leva. Framebuffers2x2/4x4 ficam para a próxima.

## Comece pelos hashes

1. Execute `hash`, `hash-n3`, `hash-n4`, `hash-n3-n4`.
2. Compare os oito valores H1/H10/H100/H500/H1000/H1500/H2000/HEND. Devem ser iguais entre as quatro ROMs. Envie foto com nomes e valores. Esses hashes testam o tilemap desta demo (excluem a linha0 deFPS); não validam áudio/CRAM nem são prova matemática de igualdade.
3. Rode `diag-control`, `diag-n3`, `diag-n4`, `diag-n3-n4`:erro0,2134frames e pico de pilha abaixo de2560B. A linha BOOT/PLAY separa o pico anterior ao timedemo e o posterior; SP mínimo continua sendo o mínimo desde o boot. PLAY inclui o custo do próprio diagnóstico.
4. Execute as ROMs de desempenho `control`, `n3`, `n4`, `n3-n4`, `f1`. Compare tempo com `control` da mesma sessão; somente depois leve a melhor ao hardware junto do controle.

## Testes de memória/vídeo

|Variante|Propósito|Expectativa a testar|
|---|---|---|
|f1|Resultados e erros sem reinicializarVDP|demo completa e tela de texto; tempo semelhante ao controle|
|diag-f1|Diagnóstico pareado doF1|erro0|
|f1-s5|Fila/bufferDMA menores, comF1|deve terminar; heap menor é esperado|
|diag-f1-s5|Diagnóstico pareado|erro0, não compararFPS|
|probe-s5|S5 com inicialização antiga da tela final|**pode travar ao exibir resultados**, hipótesefont/heap|
|v2-static|Snapshot2128B estático antes do boot|**pode travar antes da demo**, hipótesefont/heap|
|v2c|Snapshot alocado depois do boot +F1|deve permitir testarVBlank sem o temporário de sprites problemático|
|diag-v2c|Memória/pilha doV2c|erro0, heap menor esperado|
|hash-v2c|Exatidão doV2c|mesmos oito hashes dehash|

`v2-static` e `probe-s5` são as DUAS sondas de falha prevista. Os nomes e o heap-report.txt as identificam. Não são candidatas de desempenho; anote se a tela é preta, cor única ou a demo congelada e se o jogo chegou a começar/terminar. Não confundir a previsão do modelo com a causa já comprovada da falha. Não habilitarSPRTEMP_DYNAMIC.

## Contadores e perfil

`cnt` mostra eventos por quadro, incluindoSEG COLUMNS eTEX SKIPPABLE. A leitura anterior de1640,6tangentes não fecha com os demais contadores:estaROM substitui a medição. TAN16+TAN32 deve ser≤SEG COLUMNS. Não usarFPS decontadores para ranking.

`prof` e `prof-n3-n4` fazem amostragem dePC porHInt e gravam histograma naSRAM. São diagnósticos opcionais; usamSRAM e têm overhead/vieses, especialmenteDMA comIRQ mascarada. Ao terminar, feche oBlastEm normalmente para salvar o arquivo.sram. Envie o.sram e o.elf correspondente da MESMA variante. Leitor incluído emr21_profile.py:

```fish
python3 r21_profile.py /caminho/arquivo.sram doom-md-r21-prof.elf --buckets
```

O caminho do arquivo deSRAM depende da instalação doBlastEm/cartucho. O renderizador das outrasROMs continua usandoRAM principal, sem exigirSRAM.

## Opções

N3=estado do laço de paredes em variáveis locais;N4=pula preparo de textura quando nenhum tier/masked vai lê-la. Não há garantia de ganho até medir comGCC15.2. `f1` não altera o render; evita pedir novamente o bloco de3082B usado pela fonteSGDK ao mostrar resultados/erros. V2c conserva oV3 da base e muda o agendamento de vídeo paraVBlank.

OZIP contém24BINs,ELFs correspondentes,flags,logs,hashes,matriz,orçamento deheap e evidência deCPU. Probes.raw NÃO sãoROMs deMegaDrive. Build bem-sucedido e testeCPU não significam validação da demo no emulador/hardware.
