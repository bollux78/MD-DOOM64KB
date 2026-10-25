Título: [Cláudio][EXPERIMENTAL] R68 — onde vai o tempo (log por quadro + amostrador de PC, diagnóstico)
Responsável: Cláudio
Base: exp-r66-claudio-colpair @ f5a9daa7a0bd7225bbc227630defc73c67c34f1e
Branch: exp-claudio-r68-profiling-20261025
Arquivos-alvo: src/d_main.c, src/r_draw.c, src/r22_video.inc, src/p_sight.c, src/i_genesisv.c, src/r68_prof.{h,c}, src/r68_prof_hint.s, scripts/lab/{build_r35_linear.fish,build_r68.py,r68_capture.py,test_r68.py,check_r68_inert.py}
Hipótese: o FPS médio é dominado por poucos quadros pesados; medir a distribuição de custo, a carga que a explica e o perfil de funções nos quadros lentos e rápidos antes de desenhar qualquer governador de qualidade.
Controle: R66 PERF (r66-perf), H40, crop H/V16, demais opções iguais. Flag única: -DDOOM_R68_PROF.
Testes feitos (host): inércia sem a flag == R66; layout C == leitor == assembly; modelo de custo; captura contra RSP simulado. NÃO feitos: compilação m68k, BlastEm.
Pendências: build (BSS <= 57.920), captura (<= 10.000 quadros do emulador), devolver report.md.
Resultado de desempenho: nenhum (build de diagnóstico, nunca usar como medida de FPS).
Decisão solicitada ao mantenedor: TESTAR (compilar e capturar).
Estado: PRONTO PARA REVISÃO
Proposta de workflow (inativa, para o mantenedor revisar e mover): docs/agent-handoffs/proposals/r68-prof-build.workflow.proposal.yml (somente workflow_dispatch, grupo de concorrência próprio, controle R66 byte a byte contra o run 40231459814, captura <= 10.000 quadros).
