# Manifold / Mega EverDrive X7 — bissecção de SSF e 12 MiB

Data: 2026-11-17. Estado: teste preparado, ainda NÃO confirmado no X7. Não incrementar rXXX.
Branch experimental: exp-manifold-m14-x7-ssf-probe.

## Base experimental

A ROM estática de 128 KiB do Tile Palette Studio abriu Baixo+Start, Save State e Load State no X7 físico. O Manifold de 12 MiB, embora execute seu menu, não abriu o menu X7 nas tentativas r087, r088 e r088b. Tirar o header SSF do Manifold danifica a exibição dos gráficos dos bancos mapeados. Atribuir a falha apenas ao controle, ao SSF ou ao tamanho seria prematuro.

## Mudança no código Manifold

Em experiments/DOOM_Manifold_E1M1/tools/m14/multimap/crt0.s, stub30 agora lê o status VDP (0xC00004) antes de restaurar os registradores e executar RTE na fase do menu de fases (flag MVIN). Na fase do mapa, preserva o encaminhamento original para o SGDK _VINT, sem antecipar leitura do status. Esta mudança foi compilada com m68k-linux-gnu-as; NÃO foi testada no X7 e não altera a branch principal.

## Matriz de nove ROMs sintéticas

Workflow: .github/workflows/manifold-x7-ssf-probe.yml.
Script: experiments/DOOM_Manifold_E1M1/tools/m14/x7_ssf_probe.py.
Todas as ROMs derivam do binário exato de diagnóstico comprovado no X7; contêm apenas tiles coloridos sintéticos, sem WAD.

1. x7-a-original-128k.bin — controle idêntico ao que funcionou.
2. x7-b-md-4m.bin — mesmo programa, ROM de 4 MiB, header Mega Drive.
3. x7-c-ssf-4m.bin — mesma ROM de 4 MiB, mas header SEGA SSF.
4. x7-d-ssf-8m.bin — SSF, ROM de 8 MiB.
5. x7-e-ssf-12m.bin — SSF, ROM de 12 MiB.
6. x7-f-md-12m.bin — ROM de 12 MiB com header normal (controle de tamanho).
7. x7-g-ssf-12m-banks.bin — SSF e escritas de identidade em A130F3..FF.
8. x7-h-ssf-12m-sram-toggle.bin — SSF com SRAM ON/OFF por A130F1.
9. x7-i-ssf-12m-sram-on.bin — SSF com SRAM ON por A130F1.

## Protocolo no X7

Copiar os .bin para o SD e iniciar no Mega Drive sem 32X. Confirmar se a imagem de tiles coloridos aparece, se o LED do X7 acende em Baixo+Start, se o menu abre e se Save/Load funcionam. Fazer 1→5 primeiro. Com os resultados é possível distinguir efeito do header SSF de efeito do tamanho e das escritas dos bancos.

Se a variante x7-c falhar e x7-b funcionar, suspeitar do modo SSF. Se x7-c funcionar e x7-d/e falharem, suspeitar do comprimento. Se x7-e funcionar e x7-g/h falharem, suspeitar das escritas mapper/SRAM. Se todas funcionarem, suspeitar das peculiaridades do boot e das IRQs do Manifold. As ROMs não acessam conteúdo acima do banco zero, então a matriz não testa validade do mapeamento dos gráficos.

O X7 anuncia tamanho máximo de ROM de 15 MiB, mas isso não prova suporte ao menu in-game em SSF. O manual antigo da linha Mega EverDrive excluía SSF do menu, mas não é prova conclusiva para a geração X7.

IMPORTANTE: Não publicar uma ROM completa do Manifold gerada a partir de WAD privado. Não remover SSF do jogo completo. Não substituir o handler SGDK. Não marcar a solução aprovada antes de teste no cartucho.
