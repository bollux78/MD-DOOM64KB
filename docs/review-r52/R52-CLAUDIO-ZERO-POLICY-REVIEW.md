# R52 — Auditoria da correção do Cláudio (zero-policy, 22/10/2026)

## Pacote auditado
Arquivo recebido: `doom_md_sessao_r47_r52.zip`.
Novos componentes:
- `r52-ab-gerador/gen_r52_ab.py` — gerador revisado com `--zero-policy forbid|allow`;
- `r52-ab-gerador/test_r52_ab.py` — oráculo estrutural;
- `exemplo_forbid_near25` e `exemplo_allow_near25` — saídas de referência, header/report;
- patch original do Cláudio, mantido no subdiretório `patch_claudio/`.

## Resultado da verificação local (sem WAD do checkout)
- Ambos os arquivos de exemplo têm SHA-256 do cabeçalho correspondente ao relatório.
- Ambos contêm 2 paletas de 14×16 entradas, 2 LUTs de 256 índices e 2 LUTs compostas de 34×256 entradas.
- Todas as palavras de CRAM cumprem máscara `0x0EEE`; slot 0 é zero em PAL0 e PAL1 em todas as 14 subpaletas.
- `forbid`: 0 referências a índice zero em cada uma das duas LUTs.
- `allow`: 34 referências a zero em even e 27 em odd — conforme documentado.
- Sintaxe dos scripts válida; o otimizador passou em teste sintético isolando a seleção de índices.
- **Não foi realizado** o teste de WAD real, regeneração integral ou compilação SGDK nesta auditoria. O `test_r52_ab.py` completo necessita do WAD do checkout.

## Métricas de referência (somente proxy offline)
| Política, near25 | ΔE76 com fusão ideal ↓ | ΔE76 sem fusão ↓ | tons estimados (peso ≥0,1%) | avisos de subpaleta |
|---|---:|---:|---:|---:|
| `forbid` | 6,46 | 10,73 | 39 | 0 |
| `allow` | 4,88 | 8,00 | 38 | 4 |
| VF clássico (baseline) | 15,89 | 15,89 | 13 | — |

`allow` é mais fiel para PLAYPAL normal (subpaleta 0) no modelo, mas apresenta regressões em 5–8 (efeitos vermelhos de dano); `forbid` evita essas regressões na amostra. **Nenhum desses números é FPS ou captura do Mega Drive.**

## Parecer
**Correção aprovada estruturalmente para experimentação**, não para substituir automaticamente a versão de jogo. Recomendo `forbid` como primeira ROM de validação, e `allow` como comparação controlada após avaliar a transparência sob o mapeamento Pair-V. No Pair-V A/B, 0 pode revelar o backdrop preto em regiões nas quais a outra camada é transparente, portanto `allow` não é necessariamente um defeito visual; precisa de teste real de prioridade/viewport/HUD.

## Integração exigida antes do runner
1. Não substituir inadvertidamente a R52 A/B inicial: ela contém LUTs estáticas e reparo simplificado de preto; NÃO equivale às LUTs reotimizadas do Cláudio.
2. Usar o gerador completo após os insumos reais da WAD e `scripts/genpal.py` estarem presentes, por exemplo `python3 scripts/lab/gen_r52_ab.py --repo . --out src --mode near25 --zero-policy forbid --no-preview`.
3. Adaptar os consumidores de CRAM: saída do Cláudio usa `r52_pal0[224]` e `r52_pal1[224]` planos, não `[14][16]`. Selecionar `r52_pal0+sub*16`, `r52_pal1+sub*16`; no restauro de arte nativa usar o início das LUTs.
4. Compor opcionalmente `COLORMAP` por paridade com `r52_comp_even/odd`; fallback seguro para mapas atípicos fora do `fullcolormap`.
5. Tornar NumPy disponível de maneira controlada no runner (sem presumir que esteja instalado). `test_r52_ab.py` deve validar cabeçalho/LUTs contra o WAD efetivamente utilizado.
6. Auditar a cor da fonte/HUD: textos usam atributos da PAL0 atual, cuja reorganização pode alterar contraste ou legibilidade.
7. Comparar N25-forbid, N25-allow e L32-forbid no mesmo frame de E1M1, com captura sem filtros e com simulação CRT, além de DEMO3 PERF.
8. Repetir regressões de mudança de subpaleta (danos 5–8, itens), menu, retorno de benchmark, memória e hardware real.

## Estado do GitHub
A branch `r52-ab-colormix-matrix` conserva o experimento A/B original; este documento é **somente auditoria**. Não substituir ou cancelar o workflow enfileirado sem separar os resultados da primeira matriz. É recomendável preparar a revisão do gerador em branch independente, depois da validação inicial ou como segunda execução.
