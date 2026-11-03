# DOOM-MD — Portões de regressão automatizados (R116 em diante)

**Base:** pacote de demos do Cláudio, `exp-claudio-r116-demotest-20261102`. Trabalho experimental na branch `exp-chatgpt-r116-demotest-regression-20261102`; não mesclar automaticamente.

## Estado verificado em 02/11/2026 (São Paulo)

- Run [41560582340](https://github.com/bollux78/MD-DOOM64KB/actions/runs/41560582340): build, BSS e smoke do PLAY passaram, mas as **10 sondas de demo retornaram FAIL**; o workflow ficou verde indevidamente. Nenhuma sincronização foi comprovada.
- Run [41561527379](https://github.com/bollux78/MD-DOOM64KB/actions/runs/41561527379): gate de retorno não-zero corrigido. A sonda encontrou um símbolo ausente (`G_DoPlayDemo`, função estática otimizável) e a execução ficou vermelha, como deve.
- A versão de teste subsequente usa `G_Ticker` como ponto de instrumentação, confirma `r116_active` e exige todos os casos aprovados para retornar código zero.
- ROMs R116 PL/PF: 3.932.160 bytes cada, BSS 57.884/57.920 bytes (**somente 36 bytes de folga**). Evitar novos buffers em BSS; sondas e relatórios no host.

## Condições mínimas para aceitar uma nova otimização

1. **Integridade e arranque:** ROM <= 4 MiB; BSS <= 57.920 bytes; inicialização PLAY sem `I_Error`; hashes/identidade das ROMs registrados.
2. **Lógica e sincronização:** replay de demos independentes E1M1–E1M9, seleção da gravação comprovada, mesmo mapa, `leveltime` da referência ±1 tic, 100% kills/secrets nos UV-Max. Comparar depois hashes do estado do jogador, RNG, thinkers e objetos a cada tic para identificar a primeira divergência. Um timeout ou fim do emulador **não prova sincronização nem dessincronização**.
3. **Memória em combate:** `zone_min_total`, maior bloco livre, uso de SRAM e pico de heap/stack por mapa; verificar também save/load e corrupção de slot.
4. **Imagem:** capturas reais de framebuffer/VDP em tics fixos, comparando apenas configurações iguais; matriz H32/H40, recortes, A2/L3, Shadow OFF/ON, HUD, pausa do render no menu, sprites e pisos. Diferenças intencionais precisam ser classificadas.
5. **Desempenho:** mesma demo, frames, IA (Normal para controle; Low medida separadamente), recorte, áudio, perfil, Shadow e frequência NTSC. Reportar média/mín./máx., tempo e variação; repetir ganhos pequenos antes de promover.

## Limites e metodologia de execução

- Respeitar o limite operacional de **10.000 quadros emulados por processo**. Demos longas necessitam checkpoints/savestates em trechos, ou execução determinística da lógica fora do ritmo de vídeo, com validação de equivalência.
- E1M6 UV-Max tem 7.099 tics, cerca de 12.170 quadros NTSC a 35 tics/s; não cabe num único processo limitado a 9.800 quadros em condições normais.
- Cada linha do relatório deve ter status separado: `PASS`, `FAIL_SYNC`, `FAIL_RUNTIME` ou `INCONCLUSIVE_LIMIT`. **Qualquer resultado diferente de PASS impede CI verde**, mas mantém relatórios publicados.
- ROMs, ELFs e demos de terceiros permanecem somente na pasta privada do runner. Artefatos de GitHub contêm **somente logs, estatísticas, manifests e hashes**, sem redistribuição dos arquivos privados.

## Próximas implementações

1. Concluir a sonda R116 com confirmação de seleção, tratamento de limites e códigos de retorno corretos.
2. Primeiro aprovar E1M1 e outros casos curtos, separando erro de instrumentação de real incompatibilidade de demo.
3. Criar snapshots/checkpoints para demos longas e oráculo de estados por tic do DOOM 1.9.
4. Integrar capturas gráficas e matriz A/B de FPS. A otimização só é promovida quando passa os portões relevantes.

**Regra:** workflow verde significa testes relevantes efetivamente aprovados; compilação bem-sucedida sozinha nunca equivale a compatibilidade de gameplay.
