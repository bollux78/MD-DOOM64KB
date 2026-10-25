# AGENTS.md — Protocolo de colaboração entre Cláudio (Claude), ChatGPT e o mantenedor

**Projeto:** [bollux78/MD-DOOM64KB](https://github.com/bollux78/MD-DOOM64KB)  
**Data desta convenção:** 25/10/2026  
**Natureza:** regras operacionais propostas para impedir conflitos de Git, regressões e execuções descoordenadas de CI.  
**Autoridade final:** mantenedor humano. Estas regras NÃO são autorização para mesclar, excluir ou executar mudanças potencialmente perigosas.

> **Para o Cláudio:** você e o ChatGPT podem consultar e modificar o GitHub, mas **não compartilham automaticamente memória, contexto, filas de tarefas ou estado da conversa**. GitHub (Issues, PRs, commits, comentários, artifacts) é o meio de coordenação; o mantenedor decide a direção e aprova a promoção de versões.

## 1. Estado do projeto e regras permanentes

**O estado atual (baseline vigente, FPS de referência, experimentos aceitos/rejeitados, plano) vive em [`docs/STATE.md`](docs/STATE.md), a fonte única.** Este arquivo contém só regras permanentes. Leia o `docs/STATE.md` antes de programar; quem muda o estado o atualiza no mesmo PR.

- **Objetivo:** executar o máximo possível da lógica original de DOOM no Mega Drive, com jogo reconhecível, agradável e jogável. Precisão matemática e igualdade bit a bit do framebuffer NÃO são requisitos das otimizações visuais aproximadas; clipping, geometria coerente, portas, colisões, IA, sprites e estabilidade continuam essenciais.
- **ASM não é obrigatório:** escolher C, assembly ou solução mista pelo desempenho real, segurança e legibilidade. Não converter código vencedor para ASM por preferência.
- Experimentos rejeitados (ver `docs/STATE.md`) não são reintroduzidos como novidade nem mesclados sem nova decisão explícita do mantenedor.

**Branches históricas que não devem ser modificadas diretamente:**

- `exp-r60-wall-pair-asm` — R60.
- `exp-r60-r64a-prologue-memory-safe` — R64A.
- `exp-r66-claudio-colpair` — R66, referência aprovada.
- `exp-r67-aggressive-texture-groups` — experimento rejeitado, somente para consulta.

**Atenção:** a branch padrão do GitHub pode NÃO ser a melhor base técnica (por exemplo, `fullscreen`). Para iniciar desenvolvimento, consultar a branch R66 e seu **SHA exato atual** no GitHub, registrar o SHA no Issue/PR e confirmar se algum trabalho mais recente já foi aprovado. **Nunca assumir que `main`, `master` ou a branch padrão corresponde à R66.**

## 2. Papéis e poderes de decisão

| Participante | Responsabilidade principal | Não fazer sem o mantenedor |
|---|---|---|
| **Cláudio / Claude (navegador)** | Investigar algoritmos, otimizar renderer/ASM, propor e implementar patches em **branches próprias**, produzir estimativas qualificadas e oráculos, documentar riscos | Alterar a baseline, apagar versões, mesclar mudanças, disparar workflows novos de risco ou declarar aprovação visual |
| **ChatGPT** | Revisar patches, verificar integração com SGDK/MarsDev, auditar flags/ABI/BSS, construir matrizes A/B, interpretar logs e benchmarks, organizar ROMs/artifacts e fazer revisão independente | Sobrescrever a branch do Cláudio, mesclar/promover versões sem aprovação ou tratar smoke test como prova de fidelidade |
| **Mantenedor humano** | Escolher prioridades, aprovar experimentos de maior risco, julgar qualidade visual/jogabilidade no BlastEm e no Mega Drive, autorizar promoções, merges e descartes | — |

**Ambiente do Cláudio:** trabalha no Claude Code na nuvem, com o repositório clonado, Python e gcc de host. **Não tem compilador m68k nem BlastEm.** Seus testes são em host (oráculos, harness com stubs, testes de inércia e de layout) e **não substituem** a compilação m68k, o emulador, o hardware ou o julgamento visual do mantenedor. Todo resultado do Cláudio deve dizer o que foi e o que não foi verificado.

A divisão é prática, não absoluta: ambos os agentes podem pesquisar, testar e compilar **desde que respeitem ownership de branch e o plano registrado**. Nenhum agente deve representar o outro como tendo aprovado algo sem declaração explícita.

## 3. Regra de ouro: uma branch por agente, por experimento

1. **Nunca fazer commit diretamente** nas branches de referência nem na branch ativa de outro agente.
2. Cláudio usa `exp-claudio-<tema>-<data>`; ChatGPT usa `exp-chatgpt-<tema>-<data>`. Ex.: `exp-claudio-r68-scale-lut-20261025`.
3. Anotar no primeiro commit/descrição do PR: **branch-base + SHA**, propósito, arquivos que serão modificados, flags, comparador e responsável.
4. Trabalhar com commits pequenos e temáticos. Não misturar duas ideias de performance nem refatoração cosmética em uma rodada A/B.
5. Para o mesmo arquivo crítico, sobretudo `src/r_draw.c`, `src/r22_video.inc`, ASM de parede e scripts de build, **trabalhar em branches separadas**, mesmo que ambos estejam implementando hipóteses diferentes. Não forçar push para resolver divergência.
6. Nunca executar `push --force`, reset destrutivo, exclusão de branches ou limpeza de ROMs/artifacts de outro agente sem autorização expressa do mantenedor.
7. Quando houver necessidade de integrar trabalho dos dois: abrir PRs independentes, revisar o diff, escolher a ordem e **rebase/cherry-pick somente na própria branch** após consulta e aprovação. Executar novo A/B depois da integração (ganhos não são necessariamente aditivos).
8. **Pull Request não é permissão para merge.** Marcar `EXPERIMENTAL` até a avaliação do mantenedor.

## 4. Protocolo de reserva de tarefas (evita trabalho duplicado)

Antes de iniciar qualquer intervenção:

1. Consultar a lista de **Issues e PRs abertos**, branches relacionadas e os últimos commits/workflows relevantes.
2. Reservar o trabalho em uma **Issue existente** ou criar uma Issue curta; caso o conector não permita Issues, criar/atualizar `docs/agent-handoffs/<tema>.md` na **própria branch**.
3. Registrar o dono (`Cláudio` ou `ChatGPT`), o SHA da base, o objetivo técnico, arquivos-alvo e o estado: `PROPOSTO`, `EM DESENVOLVIMENTO`, `PRONTO PARA REVISÃO`, `TESTE DO MANTENEDOR`, `APROVADO` ou `REJEITADO`.
4. O segundo agente pode revisar e comentar, mas **não deve implementar a mesma hipótese em paralelo** sem combinar previamente via Issue/PR ou mediação do mantenedor.
5. Se o trabalho esbarrar em branch, arquivo ou workflow do outro agente, **interromper a edição e registrar o conflito**. Não tentar “consertar” a branch alheia silenciosamente.

**Modelo de registro:**

```text
Título: [Cláudio][EXPERIMENTAL] R68 — hipótese de escala simplificada
Base: exp-r66-claudio-colpair @ <SHA verificado>
Branch: exp-claudio-r68-scale-lut-AAAAMMDD
Arquivos-alvo: src/r_draw.c, scripts/lab/...
Hipótese: reduzir divisão/recíproca por segmento mantendo erro visual discreto
Controle: R66 PERF, H40, crop H/V16, CM e demais opções iguais
Testes: BSS, smoke, A/B DEMO3, PLAY visual, hardware quando selecionada
Bloqueios: nenhum / arquivo compartilhado / runner em uso
Estado: EM DESENVOLVIMENTO
```

## 5. Compilação e GitHub Actions — runner self-hosted

- O runner executa código com recursos e permissões do computador hospedeiro. **Tratar alterações em `.github/workflows/`, scripts de shell, downloads executáveis e ações externas como alterações sensíveis.** Não executar workflows alterados por terceiros sem revisão do mantenedor. Preferir workflows conhecidos e permissões mínimas.
- A capacidade de um agente alterar `.github/workflows/` depende das permissões concedidas ao aplicativo GitHub em uso; **não presumir que ela exista nem que não exista**. Mesmo quando tecnicamente possível, valem as regras abaixo.
- Cláudio pode propor workflows e solicitar execução por Issue/PR, mas **não deve alterar ou disparar rotinas novas no runner self-hosted sem autorização do mantenedor**. ChatGPT segue a mesma regra em mudanças de segurança ou permissões.
- Nunca ler, registrar ou exibir tokens, secrets, chaves SSH, variáveis sensíveis, arquivos pessoais do runner ou dados fora do projeto. Não adicionar comandos destrutivos/privilegiados nem instalar ferramentas arbitrárias.
- Usar **nomes de workflows e grupos de concorrência exclusivos** por experimento para não cancelar builds de outro agente. Não usar `cancel-in-progress: true` em grupos compartilhados.
- Limitar testes automatizados BlastEm a **10.000 frames emulados por invocação** (padrão). O DEMO3 completo do jogo tem **2.134 quadros desenhados**, que não são a mesma contagem do `-b` do emulador; com ~8 VBlanks por quadro de jogo, a **estimativa** é de ~18.000 quadros emulados para o DEMO3 inteiro (varia por build e cena, não é valor universal). Exceções específicas, quando necessárias para validação, dependem de autorização explícita do mantenedor.
- Manter **ROM <= 4 MiB** e conferir mapper/SRAM. O tamanho típico atual é 2.883.584 bytes; não tratá-lo como teto universal.
- Limite conservador atual de **BSS <= 57.920 B**. R66 PERF tinha 57.900 B e PLAY 57.908 B. Não assumir folga maior sem reauditoria; preferir zero BSS novo e auditar heap, stack e SRAM além de BSS.
- Verificar flag exata por ROM, presença do kernel ASM esperado, tabelas de cores, headers/identidades da ROM, BSS, ROM, stack, integridade e testes de menu. `exit 0` do BlastEm não garante correção gráfica.
- Guardar `.bin` de teste, `.elf`, flags, hashes, disassembly, logs, benchmark e manifesto em **GitHub Actions artifacts**. Não despejar ROMs e dumps grandes no Git sem necessidade.

## 6. Comparação de desempenho e qualidade

**Controle obrigatório para novos experimentos:** R66, **7,21 FPS no DEMO3 completo**, sempre sob **clock original do Mega Drive (~7,67 MHz), NTSC 60 Hz, H40, crop H/V16**, mesmo perfil de cores e conteúdo. O overclock pessoal de 13,4 MHz NÃO entra nas metas nem nos resultados oficiais.

- Primeiros filtros: build, segurança de RAM, inicialização, DEMO3 curto/prefixos e detecção de falhas de desenho ou estabilidade.
- **A/B limpo:** pelo menos três amostragens por ROM para diferenças pequenas quando viável; usar contadores VBlank no emulador, não FPS do título da janela/velocidade host. Medições dos tics 64/128/256 são **prefixos**, não substituem os 2.134 quadros do DEMO3 completo.
- **Benchmark final:** o mantenedor executa o DEMO3 completo (2.134 quadros) com controle e candidato nas mesmas condições, registra FPS médio/mínimo/máximo (janela de 1s), tempo, heap, modo de vídeo, crop, perfil de cores e observações.
- **Qualidade visual decide:** framebuffers idênticos NÃO são necessários para aproximações intencionais. Comparar capturas e **jogabilidade em movimento**, principalmente paredes próximas, giro de câmera, portas, grades, céu, texturas compostas, sprites, floors/ceilings e mapas além de E1M1.
- Distorções leves de amostragem/precisão são aceitáveis se discretas. **Artefatos visíveis crescentes com ganho pequeno, buracos, oclusão errada, corrupção, instabilidade, clipping incorreto e falhas de gameplay NÃO são aceitáveis.** R67-G4/G8/G16 já falharam neste critério.
- Promover somente após demonstração de **ganho líquido relevante + qualidade aprovada pelo usuário**, sem regressões de segurança, menus, áudio ou gameplay. Não declarar “baseline nova” com base em FPS de prefixo ou artefato de CI apenas.
- Para custos de CPU: separar **contagem estática de instruções**, estimativa de ciclos, simulação HDL e medição de ROM no emulador/hardware. Não afirmar medição em FPGA se foi apenas Musashi, documentação, objdump ou hipótese. Usar Nuked-MD-FPGA/MiSTer integrado quando houver simulação real; considerar VDP/DMA/ROM/WRAM/SRAM/bus wait states.

## 7. Entrega e handoff entre agentes

Cada PR ou entrega deverá conter:

```text
Responsável: Cláudio / ChatGPT
Objetivo e hipótese:
Branch, base SHA, head SHA:
Arquivos modificados e flags:
Controle usado (hash e configuração):
Compilação e checks de BSS/ROM/ASM:
Resultados A/B (distinguir prefixos x DEMO3 completo):
Diferenças visuais esperadas / riscos:
GitHub Actions run + artifact, com links:
Pendências de teste no PLAY e hardware:
Decisão solicitada ao mantenedor: REVISAR / TESTAR / APROVAR / DESCARTAR
```

**Nunca afirmar que o outro agente “já viu”, “já compilou” ou “aprovou” sem prova no GitHub ou confirmação do mantenedor.** Os chats do Claude e do ChatGPT não se sincronizam automaticamente. O estado durável vive nos commits, Issues, PRs e artifacts registrados.

## 8. Situações de conflito e recuperação

1. **Ambos alteraram o mesmo arquivo:** parar; comparar SHAs/diffs; manter patches em branches separadas; revisão por PR; escolher sequência de integração e recompilar.
2. **Uma branch de referência recebeu commit inesperado:** não reverter às cegas; registrar hash anterior/novo e perguntar ao mantenedor. Nunca forçar push.
3. **Runner ocupado ou workflows concorrentes:** aguardar disponibilidade da fila do GitHub; não cancelar ou repetir build de outro agente para liberar capacidade. Não combinar código de duas experiências num só controle.
4. **Resultados contraditórios:** conferir ROM SHA, clock, H32/H40, crop, perfil CM, modo PERF/PLAY, estado de profiler e demais flags. Priorizar repetição A/B estrita e julgamento do mantenedor.
5. **Falha de build/testes:** conservar logs e artifact parcial; indicar claramente o gate que falhou. Não chamar ROM “aprovada” apenas porque compilou.
6. **Alteração rejeitada:** manter no histórico/branch experimental e marcar `REJEITADO`; não apagar rastros nem recriá-la sob outro nome como se fosse nova.

## 9. Mensagem de abertura ao Cláudio

> Leia integralmente este `AGENTS.md` e confirme que compreendeu as regras de coordenação. Antes de editar, consulte Issues/PRs, identifique a branch R66 e seu SHA exato, e reserve uma branch exclusivamente sua (`exp-claudio-*`). Não modifique R60, R64A, R66 nem branches do ChatGPT. Publique seus patches e relatórios no GitHub com SHA de base e links de evidências. Eu (mantenedor) decidirei quais alterações passam à versão aprovada. Não execute workflow novo/alterado no meu runner self-hosted sem minha autorização.

---

**Esta convenção pode ser revisada com aprovação do mantenedor. Em caso de divergência, decisão recente explícita do mantenedor prevalece sobre este documento.**
