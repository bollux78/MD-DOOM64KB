# Resultados e grau de validação

## Hardware

|Base|Tempo DEMO3|Observação|
|---|---:|---|
|R20c natural|195,37s|concluída pelo usuário|
|R20d R2|193,87s|referência anterior concluída|
|R20h vc-all|178,80s|11,94FPS;min4,8/max20,3;2134frames;foto17/10/2026|

R20h reduz15,07s contraR20d:7,77% menos tempo,8,43% maior vazão. A diferença de1,97s em relação ao BlastEm(176,83s) é1,11% no tempo. Não misturar hardware e emulador para atribuir ganho por opção. Não houve controle h medido no hardware nesta última sessão. Uma demo completa não prova estabilidade de todos os mapas nem qualidade de áudio.

## BlastEm — R20h

Ver CSV para20variantes de desempenho. Todas completaram2134frames.19aparecem na imagem final; control184,90s foi obtida na imagem anterior da mesma leva. V3 repetiu180,32s e color184,90s, consistentes comR20g. Melhores:vc-all176,83;vc-r5-r6-m2177,58;vc-r5-c-r6177,63.

Diagnósticos20/20 concluídos:2134frames,máscaraerro0/primeirotic0,picopilha2368/reserva2560;zona livre912/maiorbloco528. Esses números são os observados nesta demo, não limites garantidos globais. Reserva não aumenta por liberar heap SGDK. Control SGDK3124B;diag-vc-all3768B de mínimo livre/maiorbloco. Não somar zona e heap como um único espaço alocável.

O diagnóstico possui overhead:diag-vc-all179,90s não substitui176,83s do desempenho. Conclusão dos20diagnósticos e20normais confirma a matriz nesta execução. Sem repetições suficientes para intervalos de confiança: diferenças pequenas, especialmente<0,1s, não justificam conclusões finas.

V3 isolada180,32 vscontrol184,90;vc180,40vsV3180,32: color libera RAM sem ganho de tempo demonstrado. No-v3(allrender+color)181,28vsall176,83 mostra efeito deV3 na combinação completa, com possíveis interações. Não somar ganhos individuais como se independentes.

## Histórico intermediário

R20e:control191,43;HUD188,32;FPS190,88;M3189,63;S3190,23;R3196,23;all189,93. R20f-all retirouR3 e combinou aprovadas:184,90s. R20g resultados completos em `source/docs/r20g-results.md`.

Contadores anteriores porframe, apenas orientação histórica:59,3colunastexturizadas/648células;39,1spansflat/162,6células;7,2paredes1patch;33,1multi;9,4compostas;1640,6tangentes,12,1casoslarga;8,1segs;0,9sight;máximo10pendentes. Não equivalem a perfil de ciclos da vencedora.
