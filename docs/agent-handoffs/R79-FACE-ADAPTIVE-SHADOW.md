# R79 — margem do rosto e primeiras ROMs com shadow

Base: R78 `827297b2248b1c84f5c57d8b63fa85e62f8a3c11`. Data: 27/10/2026.

## Rosto

O rosto mantém o tamanho, a posição e os 42 quadros. As duas colunas externas de fundo de cada lado do bloco 32×32 ficam transparentes; eventuais pixels do rosto que avancem até essa margem são preservados. BG_B recebe pedra do próprio HUD sob o bloco, compensando sua rolagem de +4 pixels com uma célula adicional. O preto dentro do retrato usa um índice opaco. Não se corta nem se estica a arte do rosto. São quatro pixels horizontais devolvidos ao fundo no total, sem novo estado permanente em WRAM.

## ROMs

- `r79-base-pl` / `r79-base-pf`: controle, R78 com a margem corrigida; gameplay sem shadow.
- `r79-sh1-pl` / `r79-sh1-pf`: CRAM com componentes multiplicados por 1,35, arredondados e limitados a 7; seleção normal/shadow por bloco 8×8.
- `r79-sh2-pl` / `r79-sh2-pf`: mesma técnica com multiplicador 1,75.

O shadow físico é o mesmo nas duas experiências: para componente CRAM `c` em 0…7, a entrada do DAC é `N(c)=2c` e `S(c)=c`. Os fatores 1,35/1,75 são mudanças na CRAM, não controles analógicos de intensidade da sombra. Highlight não é usado. HUD fica em prioridade alta, artes estáticas desligam S/H e menu conserva a pedra escura e o texto branco.

## Geometria real

Pair-V usa tiles transparentes na metade direita de A e B, com B deslocado 4 pixels. O shadow depende das prioridades dos dois planos, inclusive nas partes transparentes. B fica sempre com prioridade baixa; a prioridade de A controla a intensidade dos quatro samples 4×4 dentro de cada bloco físico 8×8. Assim, as duas colunas vizinhas têm o mesmo estado de intensidade. NS/SN independentes não são prometidos.

Fonte primária: testes de hardware de Kabuto, seção S/H:
https://www.plutiedev.com/mirror/kabuto-hardware-notes

## Cálculo e limites

São 15 códigos opacos em cada banco: 225 combinações horizontais NN e 225 SS. O dither fino M50 é calculado depois de aplicar a intensidade a cada componente. As médias RGB/Lab são um modelo, não cores medidas em CRT.

| Perfil | Médias NN distintas R77 | Candidatas NN+SS SH1 | Após remapeamento SH1 | Candidatas NN+SS SH2 | Após remapeamento SH2 |
|---|---:|---:|---:|---:|---:|
| Hybrid Blue+ | 189 | 378 | 153 | 359 | 203 |
| A2 Full | 203 | 406 | 248 | 400 | 205 |
| L3 Detail | 210 | 420 | 232 | 405 | 231 |
| HN Smooth | 210 | 420 | 232 | 405 | 231 |

Esses números são conjuntos de médias possíveis das colunas, não cores simultâneas garantidas numa cena. A seleção compartilhada pelo bloco ainda restringe as combinações. O remapeamento pode reduzir a variedade de um perfil — especialmente Hybrid SH1 — mesmo quando surgem tons novos. Portanto estas ROMs são experiências visuais, não uma melhoria garantida.

O alvo é a saída já quantizada da R77; este primeiro pós-processamento não recupera informação de textura descartada antes. Para cada bloco, comparam-se os custos de erro Lab de seus quatro samples em N e S e escolhe-se o menor, com empate em N. Todos os 14 PLAYPALs têm mapas próprios para preservar a coerência de tintas de dano/bônus. LUTs e custos ficam na ROM. Não há framebuffer ou scratch permanente adicional. Há trabalho adicional de CPU por quadro; não afirmar ganho nem estabilidade de FPS sem DEMO3 completo.

## Verificação

- Teste dos 42 quadros do rosto: fundo transparente na margem de 2 px por lado, interior opaco e pixels da arte preservados inclusive quando avançam na margem; inclui fixture larga e WAD real.
- Testes HUD existentes, inclusive compositor C contra modelo Python.
- Teste do pós-processamento C real: quatro perfis, 14 paletas, blocos aleatórios, atributos, limites e preservação da linha superior.
- Enumeração das 65.536 combinações de dois words por perfil/paleta; custos sem overflow no somatório em 32 bits.
- CI: seis ROMs, BSS ≤57.920, ROM ≤4 MiB, 800 frames BlastEm em cada ROM (4.800 no total). O smoke não cobre visualmente menus/transições e não substitui benchmark completo.

Testar: comparação base/SH1/SH2 no mesmo ponto; chão azul, paredes neutras, céu, inimigos/arma e blocos visíveis; danos, bônus, troca dos quatro perfis, H32/H40, menu ingame, abertura/intermissão e retorno à partida. Se houver pulsação ou blocos de brilho, reportar com o nome da ROM e perfil.
