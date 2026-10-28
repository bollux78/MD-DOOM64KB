# R86 — experimentos 68000 sobre R85 all

Base: R85 all (pré-composição conservadora + SRAM tardia + reutilização MOVEP), resultado do usuário 7,57 FPS / 281,83 s / 2.134 frames. As cinco variantes são independentes; cada uma gera PLAY/PERF com nome próprio.

| Nome | Mudança |
|---|---|
| control | R85 all, renomeada para a comparação |
| u4 | Kernel Pair-V em grupos de quatro samples/dois bytes |
| u8 | Kernel Pair-V em grupos de oito samples/quatro bytes |
| geo-o3 | optimize("O3") somente em PointToAngle16, PointToDist e ScaleFromGlobalAngle |
| logic-o3 | optimize("O3") somente em PointOnDivlineSide e InterceptVector3 |

U4/U8 preservam a ordem de reads da origem, LUT, ADD/ADDX e máscara modular. As escritas do grupo usam deslocamentos constantes, com um avanço do destino por grupo. O resto de pares usa o corpo original, incluindo cabeça e cauda parciais. A metade alta de D2 guarda a quantidade de pares restantes enquanto a metade baixa serve ao DBRA dos grupos. A flag de cauda em D7 permanece intacta. Não há buffers novos nem ABI nova.

O teste host verificou 22.528 combinações de comprimento, paridade inicial, fase, step e dados aleatórios: buffers inteiros e acumuladores finais idênticos nos modelos U2/U4/U8. Ele valida aritmética/agrupamento; a validação do assembly compilado é a comparação de framebuffer no BlastEm. O workflow compila com o toolchain 68000 habitual, exige pixels idênticos em pelo menos 100 tics comuns, gate BSS 57.920 B, ROM 4 MiB e diagnóstico parcial de pilha. Ganhos de FPS ainda não medidos. Não se usam instruções 68020 ou assembly copiado do Macintosh.

## Resultado da avaliação das outras ideias

- **Desenho de duas colunas:** a proposta do Macintosh mantém duas origens independentes vivas. Aqui R_ComposeColumn compartilha tmpCache; resolver a segunda pode invalidar a primeira. Um batching ingênuo muda imagem. Uma cópia preventiva custa até 128 bytes por origem e exigiria medir cópias, chamadas e pilha; a folga estática é pequena. Portanto esta rodada não inclui uma ROM alegando implementar desenho conjunto. Um experimento posterior deve restringir-se primeiro a origens comprovadamente estáveis em ROM, ou preparar/fixar o tempo de vida das duas origens. Isso é uma limitação concreta da arquitetura atual, não prova de inviabilidade de toda implementação.
- **fastcall:** o kernel já usa registradores por ABI própria. Aplicar -mfastcall globalmente mudaria chamadas para SGDK/assembly. Esta rodada usa seleção por função sem trocar ABI; outro ABI exigiria wrappers e suporte verificado do compilador.
- **Cache de texturas completas:** a R85 já aproveita pré-composição em ROM e preserva o cache para texturas parciais. O problema dos bytes residuais, documentado na R84, continua sendo pré-requisito para eliminar todas as cópias. Não se introduz uma biblioteca RAM de texturas baseada nos 512 KiB disponíveis ao port Atari.
- **Conversão de vídeo Atari:** o MOVEP do port atende a organização planar do ST. O Mega Drive usa nosso codebook Pair-V e DMA de atributos. Acrescentar conversão planar seria trabalho adicional, não uma substituição equivalente.

Fontes comparadas: FrenkelS/Doom8088ST `1b359d393c3cb51251e36e817ea349c0b7f33630` (i_astv16.c, bast16.sh) e izne/DOOM-for-Macintosh `8abd78de45b28902b8d8b184921220b86b157dec` (DOOM/libs/Draw68K.asm, DOOM/src/R_DRAW.C). O código novo é adaptação independente ao layout e kernel existentes.

Preparação: apply_r81.py; R80_EXPERIMENTS=P1+F1 apply_r80_performance.py; R83_CANDIDATE=sprites apply_r83.py; R85_CANDIDATE=all apply_r85.py; R86_CANDIDATE=control|u4|u8|geo-o3|logic-o3 apply_r86.py. Build e comparação em .github/workflows/r86-compare.yml. Cada variante usa cópia descartável própria. O DEMO3 completo permanece com o usuário.
