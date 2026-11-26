# Análise independente Alpha2 — Werk, 26/11/2026

## Evidência
- Workflow x360 aprovado: https://github.com/bollux78/MD-DOOM64KB/actions/runs/45907783244 (job 140208580992).
- ROM autenticada; Genesis Plus GX no commit 2499cd3e3d1d8b7d0130d8b2825adb4cc608b2c0.
- 429 intervalos completos de render em dez combinações de câmera e SRAM. Dados brutos privados: ~/.local/share/ferret-research/alpha2-profile/45907783244/.
- Câmeras conforme contrato de Cláudio. Spawn forçado com FF31C6 zerado resolve célula 131 (89 paredes), não a célula 29 natural (126). No zigzag, célula 173 nas quatro direções.

| Câmera | Paredes na lista | Projeções WRAM | Despachos WRAM | Entradas no scaler WRAM | Quadro WRAM ms | Pipeline paredes WRAM ms | Quadro SRAM16 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| spawn forçado | 89 | 89 | 39 | 365,7 | 177,39 | 85,23 | 131,48 |
| zigzag 0 | 213 | 213 | 20 | 289,2 | 203,53 | 98,69 | 149,10 |
| zigzag 64 | 213 | 213 | 25 | 347,8 | 208,92 | 110,16 | 161,34 |
| zigzag 128 | 213 | 213 | 95 | 311,7 | 245,38 | 144,64 | 196,65 |
| zigzag 192 | 213 | 213 | 22 | 341,4 | 199,60 | 106,42 | 164,28 |

WRAM: ~11.520 words diretamente na porta de dados do VDP por conversão (11568 no zigzag192, possivelmente escritas adicionais durante interrupções). Cadência das rajadas confirma aproximadamente a cadência de entrada no renderer. SRAM16: zero chamadas à conversão direta, caminho 07E3EA e DMAs de 3144+3200+3200+1976 words para bancos alternados. DMAs menores de 1152 e 56 words não são a imagem 3D completa. O MAME de Cláudio tem tempos próximos da Alpha2 SRAM16; não assumir equivalência de configuração ou de temporização do emulador. As comparações R08 render-only versus Alpha2 frame inteiro favorecem R08; para comparar pipelines é preciso instrumentar os mesmos limites.

## Visibilidade: o que comprovamos
- Auditoria independente de 288 snapshots antigos no mesmo workflow: 213 referências únicas nas quatro direções do zigzag; 126 no spawn natural, 26 na porta (2 kernels), 174 no patio e 167 na escada. Nenhuma referência condicional ativa nesses snapshots; não equivale a inexistência de portas.
- 642 registros de parede no mapa original; 431 células. A lista pré-calculada exclui cerca de 67% dos registros no zigzag e 96% na porta. O tamanho da lista não depende da orientação nestas quatro poses.
- A Alpha2 efetivamente chama o projetor para cada uma das 213 referências no zigzag. 90,6%, 88,3%, 55,4% e 89,7% não chegam ao despacho. Não é correto dizer que ela projeta apenas 20-25 paredes ou que toda a vantagem vem de listas menores.
- Entradas no scaler são transições de PC de fora para a faixa de código gerado, não número exato de colunas e não incluem preenchimentos planos.
- Perfil exclusivo por PC (percentagem dos ciclos atribuídos a instruções, não tempo integral): no zigzag WRAM 0/64/128/192, visibilidade 6,24/6,08/5,17/6,34%; projeção 10,39/11,15/17,82/11,34%; kernels 12,91/15,51/18,96/15,22%; scaler parede 12,55/14,22/11,24/13,94%; conversão 29,15/28,99/24,17/29,47%. Sprites e outros completam os ciclos. Não somar como tempo inclusivo de subrotina.
- O ganho potencial é tanto rejeição barata antes da transformação quanto loops de parede e escaladores especializados; a hipótese de metade das colunas exige teste de escrita por coluna, não dedução da largura de banda.

## Trabalho paralelo
Cláudio está investigando rejeição de backface e preparação de colunas na branch R07/R08/R09+. Werk criou experimento separado: https://github.com/bollux78/MD-DOOM64KB/pull/44, máscara conservadora por célula e orientação, usando extremos Q14 sobre o bbox FRV2. 8/16/32 bins, comparação de estado completo em milhares de poses e benchmark de render nas câmeras equivalentes, baseline fixada na R09 8ec52b3. Não usa dados de visibilidade da ROM original na engine final.
PR oficial do Cláudio https://github.com/bollux78/MD-DOOM64KB/pull/42 disparado; primeira rodada falhou no checkout de ref abreviado bbd5151, não no renderer. Usar SHA completo bbd51513a9420b292fedb4ca1c8e363f9b66cc6f. Nenhum commit feito na branch do Cláudio.
