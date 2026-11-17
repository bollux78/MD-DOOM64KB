# Manifold / Mega EverDrive X7 — bissecção de SSF e 12 MiB

Data: 2026-11-17. Estado: TESTADO NO X7 REAL; A e B permitem menu, C até I não permitem menu. Não incrementar rXXX.
Branch experimental: exp-manifold-m14-x7-ssf-probe.

## Base experimental

A ROM estática de 128 KiB do Tile Palette Studio abriu Baixo+Start, Save State e Load State no X7 físico. O Manifold de 12 MiB, embora execute seu menu, não abriu o menu X7 nas tentativas r087, r088 e r088b. Tirar o header SSF do Manifold danifica a exibição dos gráficos dos bancos mapeados. Atribuir a falha apenas ao controle, ao SSF ou ao tamanho seria prematuro.

## Resultado definitivo da matriz (Mega EverDrive X7 real)

O proprietário testou as nove variantes: **somente A (128 KiB MD) e B (4 MiB MD) abriram o menu**. Variantes C/D/E/G/H/I com header `SEGA SSF` falharam, inclusive C, que mede somente 4 MiB e difere de B pelo header SSF. Variante **F (12 MiB, header MD, sem SSF)** também falhou. Portanto, foram isoladas DUAS limitações distintas: a ativação do modo SSF é suficiente para bloquear o in-game menu, e tamanho de 12 MiB por si só também impede o menu nesta configuração de X7. A matriz NÃO estabelece o limite exato de tamanho entre 4 e 12 MiB; não foi testado 5/6/8 MiB com header MD.

A leitura de VBlank e as duas fases TH podem continuar funcionando corretamente; o menu está indisponível por configuração/modo do flashcart. O manual do Mega EverDrive v2 explicitamente exclui o Super Street Fighter II e hacks grandes do menu in-game: https://manualzz.com/doc/6927682/krikzz-v2-mega-everdrive-user-manual

**Não promover para Manifold este patch de VDP/ISR como solução do X7: o modo SSF bloqueia o recurso antes de depender desse detalhe.** A alteração permanece SOMENTE nesta branch experimental; não foi confirmada na ROM Manifold em hardware.

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

Resultado obtido: B funcionou, C falhou: **SSF isolado bloqueia o menu**. F com 12 MiB e header MD também falhou: **ROM de 12 MiB sem SSF não garante o menu**. G/H/I não funcionam como esperado sob SSF. As ROMs não acessam conteúdo acima do banco zero, então a matriz não testa validade do mapeamento dos gráficos.

O X7 anuncia tamanho máximo de ROM de 15 MiB, mas isso não prova suporte ao menu in-game em SSF. O manual antigo da linha Mega EverDrive excluía SSF do menu, mas não é prova conclusiva para a geração X7.

## Decisão arquitetural

A ROM única de 12 MiB com SSF pode permanecer funcional como jogo, mas não deve anunciar suporte ao menu Save/Load do X7. Para **ter menu X7**, a alternativa de engenharia mais promissora é produzir ROMs menores, sem SSF (por exemplo, uma ROM individual por fase até 4 MiB), mantendo VBlank e polling de controle funcionais. A possibilidade de uma única ROM maior sem SSF ainda requer reprojetar a arquitetura, pois o Mega Drive endereça só 4 MiB diretamente. A alternativa de salvar progresso dentro do próprio jogo (SRAM própria) é diferente de Save State: registrar posição, vida, armas, inventário/estado determinístico, sem prometer snapshot universal. Não mexer no firmware do X7 para contornar sem evidência.

IMPORTANTE: Não publicar uma ROM completa do Manifold gerada a partir de WAD privado. Não remover SSF do jogo completo sem reprojetar o uso dos bancos (r088b corrompeu os gráficos). Não substituir handler SGDK. Não marcar a solução como aprovada enquanto o Manifold completo com X7 não foi testado.
