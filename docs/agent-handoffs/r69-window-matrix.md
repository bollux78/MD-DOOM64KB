# R69 — matriz de tamanho de janela (diagnóstico)

Estado: CONCLUÍDO (run 40333315226 OK). Resultados em docs/review-r69/R69-RESULTS.md.
Base: `exp-claudio-r68-profiling-20261025` @ 15e4768 (R66 f5a9daa + R68 inerte). R66 segue baseline (7,21 FPS).

Motivo: o perfil por instrução (run 7 do R68) é plano; não há ponto quente que dê ganho grande sem perda visual.
A alavanca restante é a área desenhada. Este run mede FPS relativo vs janela (mesmos tics do DEMO3, ROMs instrumentadas R68):
w32 (32/32), w24, w16 (=R66), w08, w00 (sem crop), h32 (modo H32, 16/16). Controle R66 reconstruído e comparado byte a byte.
Saídas: `WINDOW-MATRIX.md`, relatórios por variante, ROMs/ELFs, MANIFEST, BSS. Máx. 10.000 quadros emulados por captura.
