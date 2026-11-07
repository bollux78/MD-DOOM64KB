# Z7 — comparação independente MD/sub

## Base e autorização

Z6 **hardware PASS**, foto do usuário em 07/11/2026: 2600 TICS PASS, TRANSFER PASS/STAGE 5, 11 requests, 63309 bytes, errors=0, STATE HASH 182C31E7, AI NORMAL, input DTE1M1. A foto não prova o fallback depois de START. O usuário autorizou continuar.

Z6 executa P_Ticker real no sub; ainda não G_Ticker completo. Z7 conserva esse payload e adiciona um observador independente dentro do G_Ticker original do MD. O teste não usa resultados inferidos/copias entre processadores como referência.

## Instrumentação

- `s1e/md_observer.c`: estado apenas em Word RAM 0x61C000, sem BSS persistente no MD. Captura tic, posição XYZ, ângulo, saúde, número de thinkers com função P_MobjThinker e índice P_Random. Captura também gametic/basetic/leveltime como metadados. O tic de comparação é o ordinal de comandos, conservado em Word RAM 0x61C030 através de respawns; leveltime reinicia e não pode ser usado como eixo comum. Em 0x61C034 há o primeiro ordinal com saúde zero, amostrado em cada tic no MD.
- O builder adiciona chamadas antes do primeiro P_Ticker e depois de cada P_Ticker original. O observador só publica os checkpoints 0/100/.../2600, exclusivamente r116_active=1 (DTE1M1).
- Só na cópia gerada Z7, um wrapper em m_text.c invoca a ação original M_R116Run(1) após D_DoomMainSetup, com AI Normal e r116_norender=1. Isso inicia a demo explicitamente, preservando a inicialização original e a seleção do benchmark. Não alterar ou substituir funções de gameplay.
- `test_setup.py --ticker` captura/verifica a simulação sub. `s1e/test_md_trace.py` abre um processo BlastEm independente para o G_Ticker MD, lê os checkpoints e escreve md_trace.csv e md_clock.json privados. O sub_trace.csv vem da PRG-RAM do sub.
- `compare_logic.py` exige todas as 27 linhas; informa o primeiro checkpoint divergente, os estados nesse ponto e o primeiro checkpoint com saúde zero para cada CPU. O intervalo é de 100 tics: NÃO afirmar primeiro tic exato de divergência/morte.
- Diferença não reprova automaticamente: o usuário aceitou aproximações/alterações R128. Só traces completos e válidos habilitam a comparação.

## Limites conhecidos

- O R128 limita visão dos monstros por fase derivada de gametic e endereço de mobj (`((uintptr_t)t1)>>5` em p_sight.c gerado). Como os endereços mudam entre MD/sub, essa é uma fonte conhecida de divergência possível, ainda não causa isolada por um controle.
- R116 usa demos como entradas repetíveis de stress, sem exigir sincronização vanilla/UV-Max. Saúde zero não prova sozinha regressão do port.
- A inicialização sub Z6 não chama P_Init. Ele inicializa a lista de switches e metadados de animação por lookup de texturas. Isso precisa ser resolvido antes de considerar o ciclo de jogo totalmente integrado; P_SetupLevel e P_Ticker sozinhos não representam toda a inicialização do engine.
- Ainda não há renderização a partir do estado sub nem medição de ganho FPS.
- Z7 é diagnóstico de captura/comparação, não uma nova versão de gameplay offloaded para homologação visual.

## Rodadas

- 5e91868 / run 42425960107: sub Z6 repetiu hash 182C31E7 e 2600 tics. MD processo atingiu o limite de frames sem trace completo; não é PASS MD/comparação.
- 76fddce / run 42426291222: MD link falhou porque M_ClearMenus é static dentro de m_text.c; corrigido usando wrapper que chama M_R116Run original na mesma unidade.
- 7da33bf / run 42426572927: MD começou corretamente, mas o trace detectou leveltime reiniciando entre checkpoints 500 e 600; captura parcial foi reprovada, sem falso PASS.
- 1c2dd15: contador ordinal independente do leveltime, metadados de morte/respawn e captura completa.

## Resultado final

**Build/link PASS / captura MD PASS / captura sub PASS / comparação válida, não idêntica / workflow SUCCESS.** Run [42426895978](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42426895978), commit `1c2dd152165721f226a782f58f8f2a0e5e12d020`.

- 27 checkpoints em cada lado, todos 0/100/.../2600. O sub continua hash 182C31E7, 11 requests, 63309 bytes, 0 erros/timeouts.
- Estado inicial (tic 0) coincide: x=69206016, y=-236978176, z=0, angle=1073741824, health=100, mobjs=36, prndindex=192.
- Primeiro checkpoint divergente: **100**. Mesma posição (8703442,-212452669,6815744), angle=2181038080 e health=100. MD mobjs=37/prndindex=47; sub mobjs=39/prndindex=44.
- No checkpoint 200 há diferença também na posição/altura/saúde. Não foi isolada ainda a causa exata da divergência. A fase de visão por endereço do R128 é uma hipótese concreta, não um resultado comprovado por controle.
- Metadados MD: **primeiro tic com saúde zero 541**, **1 respawn** contado pelo R116. Ao final health=100, gametic=2599, basetic=0, leveltime=2049. Os checkpoints de 100 em 100 não registram a morte transitória MD; por isso first_dead_checkpoint_md=null no JSON não significa que não houve morte. Consultar md_metadata.json (registro por tic/contador de mortes) para esse evento.
- Sub: primeiro checkpoint morto **2300** (morte no intervalo 2201–2300, não tic exato). Final health=0, mobjs=34, prndindex=220. O teste P_Ticker não implementa todo o ciclo de respawn de G_Ticker; não afirmar paridade/jogabilidade offloaded.
- A saúde final zero não é prova isolada de bug do port: MD também morre com a gravação sob R128, em outra hora. Existem divergências reais que ainda precisam ser avaliadas.
- Artefatos privados em `/home/dan/Projetos/Personal/scd-subport-s1e-z7/run-42426895978-1/`: `doom-md-scd-s1e-z7.bin`, ELF, `sub_trace.csv`, `md_trace.csv`, `md_clock.json`, `md_metadata.json`, `comparison.json`.
- Z7 ROM inicia o benchmark MD original automaticamente após diagnóstico/START, sem renderizar durante a captura. É instrumentação de emulador; a Z6 aprovada continua sendo a referência de console.

## Próxima etapa concreta

Portar a inicialização P_Init (lookup de metadados de texturas, tabela de switches/animações) e o ciclo completo G_Ticker, incluindo rebirth/reload e decoder original. Manter o relatório de diferenças sem transformar divergência bit a bit em reprovação automática. Só depois ligar render/input contínuo MD ao estado do sub e medir FPS.

