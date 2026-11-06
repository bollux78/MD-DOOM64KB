# Sega CD: por que a lógica remota não ganha do nativo, e onde está o ganho (Cláudio para o Werk)

**Base:** `102fa31` (bateria de lógica, run 42294870972). **Estado:** diagnóstico e proposta, nada executado.

## 1. Diagnóstico estrutural (lido em `logic/main_logic.c`, `sub_logic.c` e `install.py`)
As três variantes são **RPCs síncronas e finas**. Cada chamada:
1. copia a entrada para a Word RAM;
2. faz `exchange(cmd)`: troca de banco, espera o ACK e **espera o cálculo inteiro** (`CD_DONE`);
3. faz `exchange(0,0)`: segunda troca, só para trazer o banco do resultado de volta;
4. copia o resultado de volta.

O Mega Drive fica parado do passo 2 ao 4. **Não existe paralelismo**: o tempo do sub entra inteiro no caminho crítico, somado a duas trocas, aos laços de espera e às cópias. Além disso, cada variante perde algo que o nativo tinha:

| Variante | O que o nativo faz | O que a versão remota faz | Efeito |
|---|---|---|---|
| **Visão** | `P_CrossBSPNode` intercala BSP e `P_CrossSubsector` e **para no primeiro bloqueio** | o sub percorre o BSP **inteiro** ao longo do segmento e devolve todas as folhas; o MD ainda roda `P_CrossSubsector` em cada uma | perde o early-out e soma a RPC: só pode piorar (4,89 FPS, a pior) |
| **Raios** | `R126_VisitPending` acha o mínimo e **para no primeiro obstáculo**, normalmente 1–2 varreduras de poucos itens | copia todas as fracs, faz insertion sort completo no sub e tem 2 trocas | trabalho nativo de microssegundos virou RPC: perda garantida |
| **Som** | `P_RecursiveSound` só a cada alerta (tiro) | copia as alturas de **todos** os setores, 2 trocas, devolve todos os setores | barato por si; o custo fixo domina |

**Conclusão:** do jeito que está, nenhuma das três pode ganhar. Não é falta de ajuste fino: a unidade de trabalho é pequena demais para a ida e volta, e o MD espera.

## 2. Sobre a divergência curto × demo inteira
- **FPS:** os contadores da ROM contam VBlanks emulados, então rodar 5 BlastEm ao mesmo tempo não deveria mudar o FPS. O tempo de parede, sim. Mesmo assim: refazer **em série**.
- **Suspeita principal, antes de qualquer número:** a demo **dessincronizou** em alguma variante. Se a ordem de efeitos ou o alcance do som mudarem, a partida segue outro caminho: outros monstros vivos, outra carga.
  - Nas janelas curtas os hashes bateram. Na demo inteira ninguém conferiu.
- **Teste:** `r118_logic_check.py` com checkpoints a cada 100 gametics, na demo inteira, para `sound` e `rays` contra `native`.
  - Se divergir: localizar o primeiro tic diferente. Isso é bug de equivalência, e o FPS da demo inteira **não é comparável**.
  - Se não divergir: a regressão é custo real das RPCs.
- **Por janela** (200–260, 290–300 e demo inteira), com os mesmos gametics:
  - VBlanks;
  - número de chamadas por núcleo;
  - **ticks bloqueados no MD por chamada** (das trocas e dos laços de espera, medidos com `CD_TIMER` em volta de `SCD_LogicCall`);
  - bytes copiados.

  Com isso fecha a conta: perda ≈ chamadas × custo por chamada.

## 3. Vetores de otimização, em ordem de valor
### V1. Visão **completa e assíncrona**, um tic de atraso (o protótipo que recomendo)
- **Peso:** `P_CheckSight` era **23,3% da lógica** no E1M7 (R121). É o maior alvo de lógica que existe.
- **Por que antes não rendeu:** a chamada era síncrona e parcial.

**Desenho:**
- **Residente no sub, na carga do mapa:** nodes, subsetores→segs→linhas (v1, v2, flags de dois lados, setor da frente e de trás). Tudo o que `P_CrossSubsector` usa, para a visão completa rodar no sub, incluindo as inclinações (`topslope`/`bottomslope`).
- **Pacote por tic**, montado depois de `P_PlayerThink` / no fim de `P_Ticker`:
  - altura de piso/teto de todos os setores (E1: ~200 × 4 B);
  - jogador (x, y, z, altura);
  - os monstros ativos (x, y, z, altura).
- **Resultado:** um bit por monstro, "vê o jogador", com o ID do snapshot.

**Ciclo:**
- No início do tic N+1, **uma** troca: o MD entrega o snapshot N e recebe o resultado do snapshot N−1, que o sub calculou **enquanto o MD rodava o tic N**.
- O sub já faz ACK de posse imediatamente (`sub.s`). Então a troca não espera o cálculo, só a posse. A espera só existe se o sub estiver mais lento que um tic inteiro de lógica.

**Uso:**
- `P_CheckSight(monstro, jogador)` lê o bit se o snapshot for válido para aquele monstro. Se não for (monstro novo, snapshot velho), cai no nativo.
- Outras consultas (monstro × monstro, `P_RadiusAttack`) continuam nativas.

**Comportamento:**
- O monstro reage com 1–2 tics de atraso: 30–60 ms, invisível nesse FPS. A R128 já só olha em 4 de cada 12 tics.
- **Quebra a igualdade de demo:** validar por cenas (portas, monstros parcialmente encobertos, emboscadas), não por hash de demo.

**Refuta se:**
- o tempo do MD em `P_CheckSight` não cair para perto de zero;
- a espera por troca passar de ~0,3 ms por tic;
- os VBlanks nas mesmas janelas de gametic não caírem contra o nativo.

**Teto honesto:** se a lógica for ~30–40% do quadro, a visão vale ~7–9% do quadro. É ganho real, mas de um dígito.

### V2. Som assíncrono e compacto (barato, ganho pequeno)
- **Na carga:** portais residentes.
- **Por tic:** só as **mudanças** de abertura (setores cujo piso/teto mudou: portas e elevadores), a origem e o emissor.
- **Retorno:** bitset de setores alcançados (64 B), aplicado no tic seguinte (`soundtarget`). Fazer na mesma troca do V1.
- **Refuta se** o tempo nativo de `P_RecursiveSound` já for desprezível no perfil. Nesse caso, não vale manter.

### V3. Raios: remover da expansão
O nativo R126 já para no primeiro obstáculo. Não há o que ganhar. Levar o hitscan inteiro para o sub (blockmap, interceptações e efeitos) exigiria replicar o estado de jogo que os callbacks mudam. Não recomendo.

### V4. O ganho grande continua sendo o render
- Um quadro nativo é majoritariamente render.
- **03E colunas:** o MD ainda faz BSP e empacota texels por coluna. Por isso não passou do nativo.
- **O que pode passar:** **renderer inteiro no sub, com texturas residentes**, em pipeline de um quadro: o sub desenha o quadro N enquanto o MD roda a lógica de N+1. Esse é o handoff 03E original (`SCD-03E-RENDER-CLAUDIO.md`).
- **Antes de investir:** o perfil nativo (PC sampling, `r117_profile.py`) com a fração de render × lógica no spawn e nas janelas acima. Esse número define o teto:
  - render 60% do quadro → ganho possível até ~2,5×;
  - render 30% → até ~1,4×.

## 4. Ordem sugerida
1. Logic check na demo inteira (`sound`, `rays` × `native`), mais as medidas por janela da §2. Isso fecha o diagnóstico.
2. Perfil nativo render × lógica, que dá o teto de V1 e de V4.
3. Protótipo **V1** (visão assíncrona), já com o V2 na mesma troca se o perfil mostrar som relevante.
4. Se o perfil der render ≥ 50%, priorizar o **V4** em vez de mais lógica.

Mantém: ROM única com fallback, BSS ≤ 57.920 (estado no banco 1M ou na PRG-RAM), troca por `$A12018` e nunca DMNA, nome do arquivo no header e na tela, BlastEm ≤ 10.000 quadros por execução.
