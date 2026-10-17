# Política das levas de ROMs

Instrução do usuário de17/10/2026: toda leva futura deve incluir sempre dois controles8×8:

1. `control`: timedemo, normalmente DEMO3, para comparação de desempenho.
2. `play-control`: versão jogável sem timedemo, com música E1M1, para validar menus, gameplay e transições de fase.

Os dois devem sair da mesma base de código da leva, com os mesmos parâmetros de memória/cache do controle e sem DOOM_R22_PIXEL4. Preservar os nomes distintos e entregar juntos no mesmo ZIP com as variantes experimentais da leva. Não substituir o controle jogável por uma variante4×4.

O padrão de scripts/lab/build_r22.fish inclui ambos. Builds selecionadas para entrega também devem manter o par. A workflow específica r22c-play-control gera o par8×8, e a workflow completa da R22c inclui os dois controles entre dez ROMs.
