# R20a — último teste de diagnóstico

Todas as ROMs: DEMO3, NTSC, 38x22, HUD levantado, cache 16, zona nominal 43 KiB, música E1M1, sem espera explícita de VBlank. Nenhuma otimização R20 de desempenho foi ativada. Inlining natural preservado.

## Ordem curta para hoje

1. `doom-md-r20a-both.bin`: diagnóstico + visada e render BSP iterativos.
2. `doom-md-r20a-stack.bin`: mesmo diagnóstico, ambas as travessias originais recursivas.
3. Se a primeira terminar, `doom-md-r20a-counters.bin`: coleta contagens com ambas iterativas; fotografar a tela final.

Não precisa rodar as sete hoje. As variantes `sight` e `render` isolam cada troca se both funcionar e stack travar. `control` não tem instrumentação; `dbra` acrescenta apenas o laço Flat DBRA R19 para referência. Compare FPS apenas control/dbra, nunca os diagnósticos.

Na tela final diagnosticada: mandar foto inteira. Esperamos 2134 frames. Não interpretamos essa contagem sozinha como prova de imagem ou lógica idênticas.

## Se travar

Fotografar a última imagem com a linha superior: T=tic (mod 65536), S=pico de bytes tocados da reserva, E=máscara de erros, H=mínimo amostrado livre do heap SGDK, Z=mínimo amostrado livre da zona Doom. O primeiro erro é registrado com tic completo em RAM (`r20_first_error_tic`), sem arredondar o valor.

Bits de E somam: 1=base pintada da pilha tocada; 2=marcador final SGDK alterado; 4=cadeia SGDK inválida; 8=SP observado fora da reserva; 16=zona Doom inválida. E=0 não elimina toda corrupção ou pico não observado. Dado da tela é o último enviado por DMA, podendo anteceder o defeito.

Pico e SP incluem inicialização desde main e overhead das sondas. Watermark satura na reserva. Dados são congelados antes de abrir a tela final. Não são feitas chamadas aos walkers não limitados MEM_getFree/MEM_getLargestFreeBlock. Zona é inspecionada sem canaries envolvendo ou reduzindo o heap original. O diagnóstico altera código/layout e serve como evidência, não como prova isolada de causa.

## Artefato

Um ZIP de Actions com sete BINs, ELFs correspondentes para mapear PC, flags, logs, SHA256 e auditoria de símbolos. `layout-report.txt` registra tamanhos/endereços, sem prometer igualdade de código. Falha em nm/ELF reprova o build.
