# Handoff para Cláudio — Manifold M14 H40 + pausa / SRAM (17/11/2026)

**Pedido de Bollux78:** preservar o código funcional de **pausa, save e load** e corrigir os artefatos gráficos em hardware, especialmente as **faixas pretas que piscam** associadas a H-Int/sky. Não atribuir o flicker automaticamente ao save. **Não mesclar na versão estável sem nova confirmação em console.**

## 1. Resultado confirmado pelo usuário em Mega Drive físico + Mega EverDrive X7 (SD)

- A primeira ROM SRAM H32 iniciava com tiles ausentes/corrompidos no HUD, além de instabilidade inicial de pausa/load. A ROM estava compilada, mas não aprovada.
- Uma primeira H40 carregou HUD, porém foi montada com parâmetros diferentes dos H40 históricos; exibia etiqueta **MANIFOLD** e uma parede superior espúria sobre muro.
- A **H40 de referência corrigida** (BSP=0, `SKY_MERGE=1`, inicialização antecipada do HUD, `VDP_SAFE=2`) **funcionou no hardware**, com HUD e geometria adequados. **Ainda há faixas pretas intermitentes.**
- Posteriormente, o usuário deixou explícito: **"o importante é que o codigo de save e load e pausa funciona"**. Tratar como resultado funcional de hardware relatado pelo usuário, mas não como certificação de persistência após power-cycle, todas as fases, nem teste de longa duração. Confirmar cenários de save/load com ele se necessário.
- Últimas duas ROMs experimentais foram **compiladas**, mas não há neste handoff confirmação de teste físico delas: variante r031 `SKY_GATE` e variante com otimização r079.

**Base prioritária para não regredir:** build H40 de referência **aprovada visualmente e funcional pelo usuário**, workflow abaixo. Guardar binário atual como referência antes de alterações.

## 2. ROMs e CI (todas privadas, geradas apenas no runner local)

| Variante | ROM no diretório `/home/dan/Projetos/manifold-doom/roms/` | Run | Situação |
|---|---|---|---|
| **H40 referência funcional** | `MANIFOLD-M14-H40-REFERENCE-SAVE-E1M1-X7-TEST-12MB.bin` | [44192432544](https://github.com/bollux78/MD-DOOM64KB/actions/runs/44192432544) | Compilada e testada no console; gráficos da E1M1 corrigidos, flicker permanece |
| H40 + correção sky r031 | `MANIFOLD-M14-H40-SKYGATE-R031-SAVE-E1M1-X7-12MB.bin` | [44194679152](https://github.com/bollux78/MD-DOOM64KB/actions/runs/44194679152) | CI OK; hardware **não confirmado** nesta conversa |
| H40 + otimização de IA r079, sem SKY_GATE | `MANIFOLD-M14-H40-R079-AI-SAVE-E1M1-X7-12MB.bin` | [44195339836](https://github.com/bollux78/MD-DOOM64KB/actions/runs/44195339836) | CI OK; hardware **não confirmado** nesta conversa |
| H40 inicial não equivalente à referência | `MANIFOLD-M14-NATIVE-SAVE-H40-E1M1-ONLY-X7-TEST-12MB.bin` | [44189795507](https://github.com/bollux78/MD-DOOM64KB/actions/runs/44189795507) | Geometria e etiqueta antigas; **não usar como base** |

Workflow de referência: `.github/workflows/manifold-m14-native-save-h40-reference-build.yml`.
Workflow r031: `.github/workflows/manifold-m14-native-save-h40-skygate-build.yml`.
Workflow r079: `.github/workflows/manifold-m14-native-save-h40-r079-build.yml`.

Todos usam branch `exp-manifold-m14-native-save`, mapa **E1M1 isolado**, ROM de **12 MiB**, sem upload de WAD ou ROM ao GitHub.

## 3. Código que deve ser protegido

- `experiments/DOOM_Manifold_E1M1/m01/m14_native_save.py`: injeta pausa nativa, comandos A/B/C quando pausado, restauração no boot, integração HUD/inventário; não reintroduzir o antigo reboot incondicional de START.
- `experiments/DOOM_Manifold_E1M1/tools/m14/multimap/m14_sram.h`: acesso ao SRAM SSF do X7; alternância dos dois registros, validação por checksum, requisição de load no boot, temporária troca de banco 5 por 31 e restauração de SR/Z80/mapper.
- `experiments/DOOM_Manifold_E1M1/m01/stage_rom.py`: staging das flags gráficas, `SKY_MERGE`, proteção do VDP, `m14_sky_gate` e `m14_ai_throttle`.
- `experiments/DOOM_Manifold_E1M1/tools/m14/multimap/package_native_e1m1_test.py`: menu bare-metal, link/empacotamento privado e cabeçalho SRAM. Compilação anterior precisou corrigir inline asm 68000 e disponibilizar `memcpy` freestanding.

Controles pretendidos: START pausa/retoma; com pausa ativa, A grava checkpoint, B carrega, C retorna ao menu; B no menu de boot solicita carregar checkpoint anterior. Trata-se de **checkpoint do jogador**, não save-state completo: mundo e monstros não são serializados.

Cuidado: não fazer acesso à SRAM de código executado no slot 5 durante o remapeamento. Validar restauração do banco 5, SR e posse do Z80. Evitar alterações na inicialização do VDP e no HUD enquanto investigar o flicker.

## 4. H40 de referência: flags relevantes

```sh
MANIFOLD_MAP=E1M1 MANIFOLD_START_MENU=1 MANIFOLD_HUD=doom MANIFOLD_H32=0
MANIFOLD_BSP=0 MANIFOLD_RADIUS=1 MANIFOLD_STABLE_VIEW=1
MANIFOLD_VDP_SAFE=2 MANIFOLD_HUD_TIMING=1 MANIFOLD_STATIC_REPAIR_ONCE=1
MANIFOLD_NEAR_SAFE=1 MANIFOLD_SKY_MERGE=1 MANIFOLD_SKY_CEIL_UNIFORM=0
MANIFOLD_TEX_HSTRETCH=1.0 MANIFOLD_EYE=48 MANIFOLD_OBJ_HEIGHT_PCT=80
MANIFOLD_OBJECTS=1 MANIFOLD_PICKUPS=1 MANIFOLD_DOORS=1
MANIFOLD_MONSTERS=1 MANIFOLD_MONSTERS_INACTIVE=1 MANIFOLD_HAZARDS=1
MANIFOLD_WEAPONS=1 MANIFOLD_WEAPON_FIX=1 MANIFOLD_INPUT_FIX=1
MANIFOLD_DYN_PARAMS=1 MANIFOLD_UNPACK_MAP=1 MANIFOLD_VG_MICRO=1
MANIFOLD_TEX_U=1 MANIFOLD_MUSIC=0 MANIFOLD_PERF=1
```

Não voltar para `MANIFOLD_BSP=1` / `MANIFOLD_SKY_MERGE=0` sem motivo e teste: foi a diferença crítica na primeira H40 com muro falso.

## 5. Diagnóstico das faixas pretas e revisões r031 × r079

Documento fundamental: [M14-CLAUDIO-WERK-HINT-DMA-RESPOSTA-2026-11-14.md](./M14-CLAUDIO-WERK-HINT-DMA-RESPOSTA-2026-11-14.md).

Segundo o relatório do Cláudio (atualização 15/11):
- `manifold_sky_update` escrevia **32×9 entradas do céu** via CPU com interrupções desabilitadas ao mudar `ang >> 4`; isso prejudicava a temporização de H-Int/V-Int ao girar.
- Tentativa por `DMA_QUEUE`: a fila SGDK ficava cheia e descartava operações; atualização fatiada criava faixas descendo.
- **r031** — commit [e9f0d822](https://github.com/bollux78/MD-DOOM64KB/commit/e9f0d822e3) — introduziu `MANIFOLD_SKY_GATE=1`: só atualizar o céu quando houve render de setor com `ceil_color==0` no quadro anterior; o relatório declara resultado validado no hardware para o cenário estudado.
- **r079** — commit [f6a530a](https://github.com/bollux78/MD-DOOM64KB/commit/f6a530a7853a2fbbcc93be149b07d646e818a71b) — **não é o patch de flicker**; acrescenta `MANIFOLD_AI_THROTTLE=1`, frequência adaptativa de IA sob FPS baixo. A branch atual contém a evolução r079 e outras correções; o workflow r079 ativa especificamente esse throttle.
- O usuário pediu usar **r079 como referência**; interpretar como solicitação de preservar sua geração funcional, **não como prova de que a alteração de IA elimina faixas pretas**. O workflow r079 é uma variante sobre código atual, não checkout histórico exato do commit.
- Testar a interação de `SKY_GATE` com `SKY_MERGE`, cenas de céu aberto/fechado e H-Int real; não assumir que r031 cura todas as causas de flicker de gerações posteriores.

## 6. Tarefa objetiva para Cláudio

1. Partir do **workflow H40 referência aprovado no console** (e preservar hash/binário). Comparar com o r079 desejado sem alterar o módulo SRAM/pausa.
2. Reproduzir faixas pretas **girando em área externa, andando sem girar e em interior**, comparando o mesmo trajeto/console em ROM referência e variantes r031/r079.
3. Auditar consumo de H-Int/V-Int, `manifold_sky_update`, VDP-safe VBlank, `console_tick`, filas DMA e sprite/weapon DMA; usar medições do handoff antigo, não ajustar registradores às cegas.
4. Fazer uma correção mínima de sincronização e **gerar ROM privada com outro nome**; não sobrescrever a referência funcional.
5. Regressões obrigatórias: HUD completo desde o primeiro frame, ausência do muro superior falso, START pausa/retoma sem apagar HUD, A salva, B carrega, C menu, retorno da fase, controle responsivo, estabilidade ao girar e FPS. Separadamente verificar persistência real após desligar/religar e trocar de ROM no menu do X7.
6. Reportar exatamente quais testes foram feitos em emulador versus hardware e qual ROM/hash foi aprovada antes de qualquer merge.

**Não mexer em `rXXX` estável.** O alvo é um H40 de boa aparência com as funções de pausa + save/load intactas, eliminando os artefatos de H-Int/sky.
