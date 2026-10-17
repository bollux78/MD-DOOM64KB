# MD-DOOM — handoff para nova revisão independente

Data: 17/10/2026. Leia primeiro este arquivo e depois os documentos numerados.

## Pedido ao agente revisor

Analise o código real deste pacote e proponha uma nova rodada de melhorias de desempenho e estabilidade para o Motorola 68000 original do Mega Drive, mantendo o jogo e a imagem atuais. Buscamos oportunidades adicionais às já experimentadas. Justifique cada proposta com função/arquivo, custo atual, alteração concreta, riscos e teste de equivalência. Quando possível, forneça patch e microbenchmark reproduzível, distinguindo estimativa de ganho medido. Não aplique apenas conselhos genéricos de C moderno.

A melhor combinação atual é **R20h vc-all**, DEMO3 completa no hardware a 7,67 MHz: **178,80 s, 11,94 FPS, mínimo4,8 e máximo20,3;2134 frames**. No BlastEm:176,83s/12,07FPS. Som e aparência durante a execução não foram explicitamente avaliados no relato mais recente: a foto confirma a conclusão e o placar.

## Conteúdo

- `01-estado-e-arquitetura.md`: baseline, rotinas, limitações da plataforma.
- `02-resultados.md` e `resultados-r20h.csv`: resultados e comparação correta.
- `03-experimentos-e-armadilhas.md`: o que já foi tentado e falhou.
- `04-pedido-de-revisao.md`: questões abertas e formato esperado da resposta.
- `05-reproducao-e-proveniencia.md`: build, ferramentas, limites das evidências.
- `source/`: cópia exata de TODOS os blobs do commit R20h abaixo; sem arquivos locais extras. Documentos históricos dentro dela podem estar desatualizados; este handoff prevalece para o estado atual.
- `evidence/`: ELF, fontes e probe de CPU da CI, headers SGDK usados, flags e logs da vencedora e controles, hashes dos40BINs.
- `previous-review/`: revisão independente anterior, preservada como contexto histórico, não como novas conclusões.

## Links fixados

Repositório: https://github.com/bollux78/MD-DOOM64KB

**Fonte exata:** https://github.com/bollux78/MD-DOOM64KB/tree/8d875327922a7f6bedd3142dbafda02d628c4fbd

Branch: https://github.com/bollux78/MD-DOOM64KB/tree/r20h

Motor R20g, sem mudança de produção na matriz h: https://github.com/bollux78/MD-DOOM64KB/commit/c58f7c716be57669f193a41e8e0ca65c5dda4f5c

CI: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39045984947

Pacote original de40ROMs/ELFs/logs: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39045984947/artifacts/12106045811

Este handoff não inclui WAD nem40ROMs; use o artefato original para os binários. Acesso ao artefato pode exigir login e está sujeito à retenção da CI.
