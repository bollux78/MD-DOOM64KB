# DOOM-MD — Testes automatizados de estabilidade e segurança (R116 em diante)

**Objetivo definido pelo usuário:** descobrir se o port DOOM-MD trava, corrompe dados, estoura a memória ou pode falhar no Mega Drive físico. **NÃO é objetivo reproduzir fielmente Doom 1.9**: IA, rotas de monstros, timing das demos, mortes, kills, secrets, mapas e jogabilidade podem divergir livremente quando essa divergência é intencional ou inofensiva.

**Base:** demos privadas do Cláudio na `exp-claudio-r116-demotest-20261102`. Branch de manutenção experimental: `exp-chatgpt-r116-demotest-regression-20261102`. Sem merge automático.

## Prioridade dos testes

1. **Travamentos reais:** flag `I_Error`, exceções do 68000, falha/timeout do emulador, loops sem avanço de tics, falhas de inicialização e congelamentos após menu/retorno de mapa.
2. **Memória:** ROM <= 4 MiB, BSS <= 57.920 bytes, folga de stack/heap, menor bloco livre da zone, corrupção/fragmentação, integridade da SRAM e dos slots de save/load, inclusive transição entre mapas e reinícios após morte.
3. **Estabilidade visual e funcional:** teste no BlastEm com renderização habilitada em H32/H40, recortes variados, Shadow OFF/ON, A2/L3, alternância de menus/pausa, música e transições; detectar glitches indicativos de corrupção, travamentos e regressões funcionais.
4. **Stress por mapa:** percorrer E1M1–E1M9 com sequências de entrada gravadas. Elas são **carga repetível**, NÃO gabarito de sincronia Doom 1.9. Adicionar testes randômicos determinísticos para tiro, portas, IA, muitas coisas e mortes/reloads.
5. **Desempenho:** bench A/B comparável com mesma configuração e sem perder segurança. Meta de FPS subordinada à estabilidade, não fidelidade.

## Estados das sondas R116

- `PASS_COMPLETE`: a entrada de teste terminou (fim da demo ou saída) e os dados de saúde disponíveis não mostram falha. Não afirma que o fim ocorreu no mesmo tic que Doom original.
- `PASS_WINDOW`: o emulador atingiu o limite de quadros com término normal, tics progrediram, demo selecionada foi confirmada e zone monitorada. **Só a janela observada está aprovada**; NÃO é o teste completo.
- `FAIL_RUNTIME`: `I_Error`, falha/encerramento anormal do BlastEm, timeout ou estagnação.
- `FAIL_MEMORY`: zone inconsistente ou esgotada nos pontos monitorados.
- `INCONCLUSIVE`: não foi possível validar a entrada, estado ou andamento. Bloqueia aprovação, mas NÃO prova defeito no motor.

Qualquer `FAIL_*` ou `INCONCLUSIVE` faz CI falhar. Diferenciar claramente `PASS_WINDOW` de prova de conclusão, e enviar relatórios privados sem demos/ROMs/ELFs. Se a headroom da zone cair abaixo de 1 KiB total ou 512 bytes no maior bloco, sinalizar um **alerta de memória**, que exige investigação antes de testar no console; esses limiares são prudenciais, não um diagnóstico comprovado.

## Evidência da primeira bateria

- Execução [41560582340](https://github.com/bollux78/MD-DOOM64KB/actions/runs/41560582340): compilação/smoke passou, mas a sonda antiga marcou dez `FAIL` de sincronização com o jogo original. Esses `FAIL` **não são prova de insegurança nem de corrupção**.
- Execução [41561527379](https://github.com/bollux78/MD-DOOM64KB/actions/runs/41561527379): a sonda estrita detectou símbolo estático ausente; falha de instrumentação.
- Execução [41562116058](https://github.com/bollux78/MD-DOOM64KB/actions/runs/41562116058): confirmou seleção correta da demo para 9 mapas; a maioria atingiu o limite de quadros, E1M8 terminou sem saída no mapa, e E1M5 sofreu EOF antes de observar um tic. **Reavaliar pelo objetivo de estabilidade, principalmente o caso E1M5**.
- ROMs R116 PL/PF: 3.932.160 bytes e BSS 57.884/57.920 bytes, **36 bytes de folga**. Preferir medições no host/RSP, sem aumentar BSS do port.

## Limites de segurança e lacunas

- Limite operacional: <= 10.000 quadros emulados por processo. `PASS_WINDOW` não cobre todo o mapa, nem prova ausência de corrupção fora dos pontos monitorados. Para testes longos, criar execução em trechos com snapshots/savestates, mantendo a mesma sequência de comandos.
- A sonda lógica com `r116_norender=1` **NÃO testa VDP, DMA, framebuffer nem a renderização real**. Uma suíte com vídeo habilitado é obrigatória antes de declarar uma ROM pronta.
- BlastEm e ferramentas de host não garantem compatibilidade com Mega Drive/flashcart físico, sobretudo temporização, SRAM, IRQ e DMA. Manter rodada final no hardware real e jamais testar uma ROM com suspeita de corrupção ativa na SRAM contendo saves importantes.
- Demos, ROMs e ELFs de terceiros ficam no runner privado; artifacts GitHub incluem somente logs, manifests, contagens e resultados.

## Próximos desenvolvimentos

1. Passar R116 à classificação segurança/stress e fazer CI sinalizar anomalias reais, sem exigir o resultado original Doom 1.9.
2. Investigar o EOF pré-tic do E1M5, sem mascará-lo como sucesso.
3. Incluir guards/canários de RAM e SRAM, testes de save/load e verificações da stack em cargas extremas.
4. Incluir testes com renderização real, H32/H40, Shadow, recortes e alternância do menu; smoke de transições E1M1–E1M9.
5. Implantar checklist físico antes de distribuir versão aprovada.

**Regra central:** priorizar estabilidade e segurança do Mega Drive, sem qualquer obrigação de fidelidade exata ao DOOM original.
