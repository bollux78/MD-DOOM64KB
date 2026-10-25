# AGENTS.md — DOOM-MD: coordenação Claude/Cláudio e ChatGPT

**Projeto:** bollux78/MD-DOOM64KB  
**Vigência proposta:** 25 de outubro de 2026  
**Responsável por aceitar mudanças:** mantenedor humano.

Este documento define como Cláudio (Claude Web), ChatGPT e o mantenedor trabalham **sem sobrescrever ou duplicar** o trabalho alheio. GitHub (Issues, PRs, commits, Actions e artifacts) é o quadro comum. As conversas dos dois agentes **não se sincronizam automaticamente**. Ler estas regras ao começar cada tarefa e confirmar no GitHub o estado atual.

## 1. Estado do projeto / versão de referência

- **R66:** baseline atualmente aprovada pelo mantenedor por desempenho e aparência. DEMO3 completo NTSC, 2.134 quadros, **7,21 FPS / 295,88 s**, clock padrão do 68000 (~7,67 MHz), H40 crop H/V 16/16, mesma cor.
- **R64A:** referência anterior, **6,91 FPS / 308,98 s**; R60 PairASM também deve ser preservada.
- **R67-G4/G8/G16:** explicitamente **REJEITADAS** pelo mantenedor. Embora entreguem 7,35/7,47/7,53 FPS, causam degradação visual perceptível e crescente; **não incorporar nem repetir sem autorização**.
- R65-P1 rejeitada por regressão. R65-P2 não demonstrou a redução de registradores prevista. Consultar os relatórios antes de reutilizar qualquer hipótese.
- O objetivo é um DOOM **reconhecível e jogável**, preservando o máximo possível do código original. Reduções de precisão no renderer podem ser estudadas **apenas se a aparência e a estabilidade compensarem**. Exatidão de framebuffer não é critério universal.
- Código C, ASM ou misto: vence o que tiver melhor desempenho real com segurança. Não converter para ASM só por preferência.

Branches históricas **não alterar diretamente**: exp-r60-wall-pair-asm, exp-r60-r64a-prologue-memory-safe, exp-r66-claudio-colpair, exp-r67-aggressive-texture-groups.

**A branch padrão do GitHub NÃO é presumidamente a baseline.** Descobrir o SHA atual da R66, registrar base SHA e confirmar aprovações posteriores antes de iniciar.

## 2. Responsabilidades e autorização

**Cláudio / Claude Web:** pesquisar novas técnicas, inspecionar C/ASM gerado, criar patches e oráculos, desenvolver **somente em suas branches** (prefixo exp-claudio-), documentar hipóteses e riscos.

**ChatGPT:** revisão independente, integração/testes em **suas branches** (prefixo exp-chatgpt-), builds controlados MarsDev/SGDK, auditoria de BSS/ABI/flags, comparação A/B, interpretação de dados e artifacts.

**Mantenedor:** aprova a prioridade, avalia visualmente o jogo e o desempenho, autoriza alteração de segurança/runner, define o vencedor e aprova qualquer promoção, merge ou exclusão.

Papéis são organizacionais, não bloqueiam revisão mútua. **Ninguém presume consentimento do outro agente ou do mantenedor.** Nenhum dos agentes deve mesclar em baseline, apagar branches/artifacts ou disparar ações potencialmente destrutivas sem aprovação humana explícita.

## 3. Branches e operações Git — prevenção de conflito

1. Cada hipótese recebe **sua própria branch** a partir de um commit SHA confirmado: exp-claudio-TEMA-AAAAMMDD ou exp-chatgpt-TEMA-AAAAMMDD. Branch de um agente nunca é área de trabalho compartilhada.
2. Registrar antes de programar: SHA de base, branch, responsável, propósito, arquivos-alvo, flags de compilação e ROM controle.
3. Não fazer commit na R60, R64A, R66 ou na branch alheia. Não force-push, reset destrutivo, exclusão/limpeza nem alteração da branch padrão.
4. Commits pequenos: **uma hipótese de otimização por rodada A/B**. Não misturar refatoração ampla com benchmarks.
5. O mesmo arquivo crítico (sobretudo src/r_draw.c, src/r22_video.inc, ASM, build scripts) pode ser alterado em experimentos **separados**, mas nunca simultaneamente na mesma branch. Se houver sobreposição, parar e avisar via Issue/PR.
6. Integrar via PRs diferentes, revisar diffs, decidir ordem de cherry-pick/rebase **na própria branch** após aprovação, e medir novamente: os ganhos podem não ser aditivos.
7. **PR aberto não é autorização para merge.** Manter status EXPERIMENTAL até aprovação do mantenedor.

## 4. Como reservar trabalho (GitHub como memória compartilhada)

Antes de qualquer implementação, olhar Issues/PRs/branches e seus commits recentes. Abrir uma Issue ou comentar em uma existente; se o conector não permitir, escrever um arquivo de handoff **na própria branch**. Especificar:
- Agente responsável; estado **PROPOSTO / EM DESENVOLVIMENTO / PRONTO PARA REVISÃO / TESTE HUMANO / APROVADO / REJEITADO**.
- Base branch+SHA, branch atual+SHA, arquivos previstos, hipótese técnica e comparação A/B.
- Link do PR, workflow, artifact, logs e pendências de revisão.

O outro agente pode revisar/comentar, mas não deve duplicar a implementação sem coordenação explícita. Não declarar que o outro agente já viu ou aprovou algo que não esteja registrado.

## 5. Runner self-hosted e segurança

O runner do GitHub Actions é **self-hosted**. Tratar alterações em .github/workflows, arquivos executáveis, scripts shell, downloads e permissões como sensíveis. **Propor mudanças de workflow antes de executá-las; exigir aprovação do mantenedor para workflows novos ou alterados que rodem no runner.** Não executar código não revisado de forks/terceiros no runner.

- Nunca expor tokens, credenciais, chaves SSH, variáveis sensíveis, arquivos pessoais, nem acessar dados externos ao projeto.
- Usar permissões mínimas de Actions, dependências aprovadas e jobs identificáveis; não instalar ferramentas arbitrárias ou usar privilégios elevados sem autorização.
- Usar nomes/concurrency groups exclusivos por experimento; não cancelar jobs do outro agente, não usar cancel-in-progress compartilhado.
- Testes BlastEm: **até 10.000 frames emulados por execução**. Isso é diferente dos 2.134 quadros **renderizados pelo DEMO3** do jogo.
- Guardar ROMs/ELFs, flags, hashes, logs, disassembly e perfis como GitHub Actions artifacts. Evitar binários volumosos diretamente no Git.
- ROM <= 4 MiB e verificar mapper/SRAM; BSS <= **57.920 B** (R66 PERF 57.900 B, PLAY 57.908 B). Preferir zero BSS novo; auditar também heap, stack e SRAM.
- Conferir ROM header/identidade, LUT/paletas, kernel ASM, flags exatas e modo PERF/PLAY. Sucesso de compilação ou exit 0 no emulador **não prova ausência de defeitos**.

## 6. Critérios A/B, precisão e aceitação

- A referência técnica corrente é a **R66 com 7,21 FPS**, CPU original ~7,67 MHz, NTSC 60 Hz, H40, crop horizontal/vertical 16/16 e mesmo perfil de cor. Overclock pessoal **não conta** para benchmarks oficiais.
- Comparar controle e candidato nas mesmas condições; usar contadores internos de VBlank/DEMO3, **não** a velocidade de emulação indicada na barra da janela.
- 3× prefixo do DEMO3 (tics 64/128/256) ajuda a triagem, mas **não substitui o benchmark completo de 2.134 quadros**. Separar claramente prefixo de benchmark completo.
- No benchmark completo registrar FPS médio, mínimo/máximo de 1s, tempo, heap, clock, H32/H40, crop, perfil de cor e ROM hash.
- **Aceitar aproximações numéricas somente se o mantenedor aprovar o resultado visual em movimento.** Não exigir byte-identidade de framebuffer quando erro deliberado é parte do experimento.
- Checar giro, deslocamento junto a paredes, textura composta, grades, portas, céu, floors, sprites, clipping, transições de fases, áudio, Start/menu rápido, H32/H40, crop e modos de cores.
- **Não aceitar** oclusão errada, rasgos, travamento, corrupção gráfica/RAM, perda clara da identidade visual ou mudança perceptível desproporcional ao FPS. O precedente R67 foi recusado precisamente por isso.
- Relatar separadamente: cálculo estático via objdump, estimativa teórica, simulação RTL realmente executada, medição BlastEm e teste físico. Não alegar ciclos FPGA/VDP/ROM/WRAM/DTACK sem simulação integrada correspondente (Nuked-MD-FPGA/MiSTer).
- Somente o mantenedor pode **promover uma nova baseline**.

## 7. Formato obrigatório de handoff/PR

Responsável e estado; objetivo; branch/base SHA/head SHA; arquivos e flags alterados; ROM controle/hash; alterações funcionais; BSS/ROM/ABI/segurança; desempenho A/B (prefixo separado de DEMO3 completo); capturas/diferenças visuais e riscos; links de workflow e artifacts; testes PLAY/hardware pendentes; decisão solicitada ao mantenedor.

**Se houver conflito:** não corrigir por conta própria a branch do outro agente. Registrar os SHAs conflitantes, comentar no PR/Issue, aguardar decisão do mantenedor e recompilar depois da resolução.

## 8. Instrução inicial ao Cláudio

> Leia integralmente este AGENTS.md. Confira a R66 aprovada, localize o SHA real da base, examine as Issues e PRs abertos e reserve a sua tarefa. Desenvolva apenas em branch exp-claudio-*. Não modifique nenhuma baseline ou branch do ChatGPT, não execute workflow novo/alterado no meu runner sem autorização e não mescle nada. Envie o link do PR/commit e os resultados para revisão independente, após o que o mantenedor decidirá os testes finais.

**Esta convenção só muda por decisão explícita do mantenedor; decisões recentes dele prevalecem.**