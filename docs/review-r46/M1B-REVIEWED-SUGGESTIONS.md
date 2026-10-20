# R46 M1B revisada — aplicação do documento DOOM_MD_OTIMIZACOES_CONSOLIDADO.md

**Base:** `r46-m1b-video-prep`. Branch desta revisão: `r46-m1b-reviewed-manual`.
O documento enviado é uma análise **R38→R40c** (branches `r38-time-profile`, `r39f-dither3-vertical`, `r40b-pixel4-text-diff`), anterior às medições R41–R46. Suas estimativas não devem substituir os benchmarks novos.

**Não foi solicitada compilação nesta etapa.** O workflow desta branch foi alterado para **somente `workflow_dispatch`**, sem gatilho `push`. Nenhuma ROM da branch revisada deve ser descrita como compilada ou aprovada até a próxima execução. Há uma CI antiga enfileirada na branch original `r46-m1b-video-prep` ([#39365018316](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39365018316)); ela é anterior a estes patches e deve ser cancelada antes de ligar o runner, para evitar trabalho duplicado. Esta conexão não possui ferramenta de cancelamento de workflow.

## Propostas efetivamente incorporadas nesta leva

| Origem do documento | Implementação na R46 M1B revisada | Critério de aprovação posterior |
|---|---|---|
| P4 / seção 3: amostragem incorreta de textura multipatch | `src/r_draw.c`: o ramo `overlapped` agora envolve `R20_WALL_DRAW(dcvars)` em `R7_VOID(6,...)`, como o ramo não composto. A composição permanece no bucket 7. Macro é inerte nas builds não instrumentadas. | Confirmar compile e que o benchmark limpo permaneça 11,80 FPS |
| Q3: ignorar tiles sólidos antes do upload | `R46_P4_PackIfDynamic` devolve 0 para tiles sólidos/inválidos **sem expandir pixels nem mexer no output**, ou índice dinâmico e oito palavras de padrões para tiles variáveis. Entrada através da tabela `R46_P4_VramOps`. Nenhum código de VDP/ISR foi habilitado. | Oracle host em 40 framebuffers, ambos os bancos, bytes de saída e sentinelas intactas; ROM 8×8 sem regressão |
| Plano seção 6: layout VDP unificado | Criada auditoria `scripts/lab/audit_r46_unified_vdp.py` com proposta de tiles do 8×8 `16–241` e dois bancos 4×4 `54–851` / `890–1687`. A auditoria registra a **sobreposição 54–241**; VRAM precisa ser regravada em cada alternância. `TILE_USER_INDEX` do 8×8 e registradores continuam como antes. | Revisão de endereços reais no ELF/SGDK e segurança VInt/DMA antes de modificar hardware na M3 |
| RAM (seção 6): riscos de +210 B | Workflow compara `.bss` real da ROM mista à ROM controle: não aceita crescimento de BSS na M1B. O framebuffer 4×4 continua usando `_s_screen` (2128 B); não há mapa adicional de 1596 B. | Boot, `MEM_getFree` e maior bloco após nível carregado. O gate BSS **não substitui** medição dinâmica do heap; controle observado pelo usuário: 1386 B SGDK livres no benchmark |
| Planejamento de throughput/VDP | Fonte documentada com ordem M2 geometria → M3 DMA/CRAM/VRAM → M4 menu. O Q3 do standalone já pulava tiles sólidos antes de escrever VRAM; o novo helper torna isso explícito para a ROM dual. | Teste de 8×8 e 4×4 separados após o dispatcher |

### Situação atualizada das propostas antigas

- **P1/P2:** já incorporadas (MOVEP SRAM e cache reaproveitado); preservar, sem refazer.
- **Q1:** implementada e medida na R41. Cerca de 46,3% das **amostras VBlank** foram atribuídas a paredes. Isso não é uma medição exata de ciclos.
- **Q2:** implementada na R42 e aprovada na R44: 4×4 de 3,01 para **3,88 FPS** no DEMO3, não 5–6 FPS (aquilo era estimativa); também aprovada a troca de fase e intermissão.
- **P3** pré-composição offline ROM: deixar para diagnóstico de texturas multipatch; verificar custo antes de comprometer ROM >2,75 MiB.
- **P5** bitmap de `validcount` na WRAM: adiar; RAM livre é escassa e exige prova de ausência de consultas com validcounts aninhados, além de hash bit a bit.
- **P6** culling em `R_AddLine`, **P7** `FixedMul/Mod`, **P8** desenrolar ASM 8×8: testes separados após coexistência, pois não são requisitos para M1B.
- **Q3** travar interrupções por linha em vez de por tile: **não implementado ainda**. Risco de atrasar VBlank além das linhas 224–232. Deve ser testado somente com upload real M3 e temporização verificada em hardware.
- **Geometria clonada por `always_inline`:** proposta para **M2**, não M1B. Ainda precisa resolver tabelas, clipping, visplanes e sprites independentes; não presumir que GCC gere dois clones idênticos por si só.
- **Arma como hardware sprite, céu em plano B, Z80/XGM2, flags `-O2/-Os/LTO`, P5 da lógica**: manter como experimentos isolados posteriores. Timedemo com um tic por quadro pode subestimar custo real da lógica, mas fator 3× é limite estimado, não medido.
- **Mapper SSF e usar Z80 para gráficos:** excluídos conforme o documento.

### Compilação futura (somente após autorização)

1. Executar primeiro os scripts `python3 scripts/lab/test_r46_m1b_vram.py`, `audit_r46_unified_vdp.py`, além dos testes R42 de parede e R44 de intermissão.
2. Cross-compilar **controle** `doom-md-r46-primary-perf`, **M1B** `doom-md-r46-m1b-perf` e `doom-md-r46-m1b-play`, verificar `R46_P4_PackIfDynamic` e os demais símbolos pelo `m68k-elf-nm`.
3. Auditar 4 MiB máximo, SRAM, header, `.bss` sem crescimento, banco VRAM e smoke BlastEm de 300 quadros.
4. Testar no BlastEm DEMO3 completa: controle e M1B devem permanecer **11,80 FPS / 180,82 s**, 2134 frames. Verificar gameplay, menu, música/SFX/dither Off/Checker/Vertical. Medir heap de execução (SGDK free / largest), não inferir apenas da BSS.

**Nenhuma ROM dual com troca em runtime está pronta nesta fase.** A R46 M1B permanece 8×8 ativo + componentes 4×4 co-linkados sem acesso ao VDP durante o jogo; isso é deliberado.
