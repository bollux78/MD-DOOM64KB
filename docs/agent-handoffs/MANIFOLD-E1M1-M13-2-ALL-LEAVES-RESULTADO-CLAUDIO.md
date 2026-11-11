# MANIFOLD E1M1 — M13.2 all-leaves: handoff para Cláudio (11/11/2026)

**Branch compartilhada:** `exp-manifold-m12-claudio`  
**Origem do teste:** [GitHub Actions #43092148217](https://github.com/bollux78/MD-DOOM64KB/actions/runs/43092148217)  
**Commit testado:** `e99f64c8a29a0b1552c60f9e0ab919b8ad79865e`  
**Workflow:** `.github/workflows/manifold-m13-werk-hud.yml` — *Manifold M13 Werk BSP all-leaves A-B H40*.  
**Artefato:** `m13-werk-bsp-all-leaves-ab-43092148217`. Build Actions **success** (não equivale a aprovação gráfica ou de desempenho).  
**Público:** Cláudio; retorno de teste visual e desempenho relatado pelo usuário. **Este handoff é apenas documentação; não muda render nem dispara build.**

## 1. Resultado observado pelo usuário

O usuário testou a variante **all-leaves** e enviou duas capturas da região externa grande de E1M1, no mesmo dia:

1. **Primeira captura:** paredes do cenário com **alturas corretas** — êxito visual específico para projeção/altura. O usuário confirmou: “a versão all leaves renderiza as paredes com alturas corretas”.
2. **Segunda captura:** o velho defeito de **perda de partes da tela em área externa grande continua**. Há um grande retângulo azul-escuro sem textura, aproximadamente no centro-direita e descendo até a borda inferior, além de outra região azul-escura na fachada à esquerda. A área restante ainda mostra construções, montanhas, céu e terreno. Não concluir que são todas “colunas não desenhadas”: a natureza exata precisa de diagnóstico.
3. **FPS relatado:** cai de aproximadamente **4 FPS para 1 FPS** com all-leaves: queda de 75% na taxa de quadros; tempo por frame equivalente ~250 ms → ~1000 ms (valores aproximados). O usuário não forneceu aqui uma captura do contador de FPS nem confirmou benchmark de câmera fixa pareada; classificar a medição como **relato de teste**, não benchmark controlado.

**Conclusão operacional:** M13.2 all-leaves **não está aprovado para promoção a renderer jogável**, apesar de melhorar alturas. Preservar seu commit e artefato como referência visual/reprodutor.

## 2. O que foi comprovado e o que NÃO foi

| Item | Evidência / estado |
|---|---|
| Build do workflow M13.2 | GitHub Actions concluiu com sucesso. |
| Alturas das paredes | Correção observada pelo usuário no primeiro enquadramento all-leaves; ainda não verificada em todos os setores/ângulos. |
| Falhas visuais em áreas abertas | Persistem na segunda captura all-leaves; causa desconhecida. |
| FPS | Relato ~4 → ~1 FPS; severa regressão, a confirmar em câmera fixa. |
| Travessia/visibilidade BSP como causa única do buraco | **Não demonstrado**. Renderizar todas as folhas não eliminou o defeito. |
| Clipping vertical, oclusão por coluna, saturação de buffers | **Hipóteses**, não diagnósticos comprovados. |
| Corrupção VRAM/DMA ou artefato da apresentação | Hipótese alternativa; não descartada por essas capturas. |

Não confundir os blocos azul-escuros da **cena 3D** com os antigos **tiles/fundo preto do HUD** dos handoffs M12/M13. Podem ter causas independentes.

## 3. Pedido específico ao Cláudio — primeiro diagnosticar, depois corrigir

**Objetivo:** alcançar a geometria correta do all-leaves, remover os buracos em áreas abertas e recuperar pelo menos a ordem de grandeza dos ~4 FPS anteriores, sem mascarar pixels ausentes ou reduzir a cena desenhada indevidamente.

### Experimento A — reprodução e localização da falha

- Ler o head atual do branch e a implementação real M13.2 antes de modificar qualquer trecho.
- Usar o **mesmo ponto/ângulo** da área externa e uma câmera fixa reprodutível, com mesmos parâmetros de resolução **H40**, mapa, posição, orientação, altura e opções de display. Se não for possível reproduzir exatamente a foto, documentar coordenadas reais do novo caso.
- Comparar **H40 limitado/control** versus **H40 all-leaves**, idealmente no mesmo build A/B e sem mudanças simultâneas de renderer. Manter ROM jogável após START.
- Capturar imagem e logs com sincronização de quadro; separar desenho do framebuffer, flip/DMA, efeito de conteúdo anterior do backbuffer e estado do HUD.
- Medir número de folhas BSP visitadas/aceitas, células/segundos/linhas e segmentos por quadro; quantos segmentos sobrevivem frustum/occlusion clipping; contagem de colunas cobertas, lacunas por coluna, razões de descarte. Instrumentar saturação/overflow de cada array/contador e verificar limites de índices com guardas.
- Traçar, para pixels/colunas dentro do bloco azul-escuro, **qual plano de parede/piso/teto deveria preencher**, se foi gerado, se foi recusado, se foi rasterizado e se foi apresentado. Captura com cores diagnósticas ou bitmap de cobertura **opt-in**, sem mudar a lógica de render do controle.
- Comparar se azul-escuro é **cor de neblina/fundo**, textura inválida, coluna sem preenchimento, textura/paleta ou resultado de falha de apresentação. A mera cor não prova a causa.
- Verificar especificamente clipping horizontal/vertical, marcadores de oclusão por coluna, atualização de limites de piso/teto e preenchimento residual — mas **sem assumir culpado**.

### Experimento B — decompor custo do 1 FPS

- Registrar tempo/ciclos por fase: travessia BSP, bounding/frustum, transformação/projeção, clipping/oclusão, paredes, piso, teto, upload/flip e overlay.
- Comparar contagens de folhas/células/seg e custo por item nas **mesmas câmeras** de controle e all-leaves. Incluir ao menos uma vista aberta problemática e uma vista interna simples; se disponível, reaproveitar as 6 câmeras fixas usadas no handoff M12.
- Separar regressão por **mais geometria processada** de regressão por **perda de oclusão/culling** ou caminho patológico em um núcleo. Não concluir antecipadamente que o custo é apenas número de folhas.
- Se puder, entregar A/B com modos de diagnóstico que desliguem isoladamente somente etapas não necessárias para medição, **sem declarar essas versões como jogáveis/aprovadas**.

### Experimento C — solução seletiva, preservando a geometria

- Não propor all-leaves bruto como solução final: 1 FPS inviável.
- Identificada a causa, construir **seleção visível eficiente, ordenada e correta**, retendo alturas originais; avaliar agrupamento BSP seguro, early-out, clipping/occlusão corrigidos e/ou cache de vértices **somente após medir**.
- Não corrigir buracos com preenchimento arbitrário sem confirmar qual superfície estava ausente.
- Critérios para propor promoção: sem blocos faltantes nas cenas de regressão, alturas corretas, sem crashes/overflows, H40 estável, FPS restaurado sem piorar HUD/VDP, teste real do usuário em console.

## 4. Referências existentes obrigatórias

- `docs/agent-handoffs/MANIFOLD-E1M1-M13-CLAUDIO-PARA-WERK.md`
- `docs/agent-handoffs/MANIFOLD-E1M1-M13-WERK-PARA-CLAUDIO.md`
- `docs/agent-handoffs/MANIFOLD-E1M1-M12-CLAUDIO-DIAGNOSTICO-HANDOFF.md` (especialmente descrição dos dois framebuffers VRAM parcialmente sobrepostos, render sem limpeza, `MANIFOLD_BSP`, `hole_diag`, contagens/custo por célula; hipóteses ainda sujeitas a validação).
- [Run M13.2 #43092148217](https://github.com/bollux78/MD-DOOM64KB/actions/runs/43092148217), artefato `m13-werk-bsp-all-leaves-ab-43092148217`.

**Capturas de referência:** as duas imagens foram anexadas pelo usuário na conversa em 11/11/2026. Não foram adicionadas como binários ao repositório neste commit; pedir ao usuário as imagens originais caso seja necessária comparação pixel a pixel. Para reconhecimento visual: imagem 1 mostra paredes/grades com alturas coerentes; imagem 2 mostra blocos azul-escuros grandes sobre a cena externa.

## 5. Regras de execução e entrega

- Trabalhar no branch compartilhado existente; criar commits pequenos, explícitos e revisáveis. Proteger a referência M13.2.
- **Não modificar código do renderer no próprio commit deste handoff.**
- Somente ROMs H40 para esta linha de desenvolvimento. Não adicionar WAD ao repo nem aos artefatos. Release apenas com aprovação expressa e teste visual.
- Não confundir CI verde ou execução headless com validação gráfica em CRT/console.
- Antes de novo build no runner, seguir a coordenação definida nos handoffs anteriores: acionamento sob solicitação do usuário.
- Retornar diagnóstico com **evidências, contagens e tempos** e as variantes A/B sugeridas; não declarar correção sem comparação e confirmação do usuário.

**Status de M13.2:** ALTURAS = melhora confirmada no cenário observado; BURACOS EM ÁREA ABERTA = persistentes; FPS = regressão grave (~4→~1); CAUSA = aberta; PRÓXIMO RESPONSÁVEL = CLÁUDIO.
