# Dread MD D01 — handoff para o Cláudio

A versão mais recente é **Combate 03**, uma ROM de 3,75 MiB com os nove mapas do Doom shareware. É uma build de teste para cartucho padrão.

[Baixar Doom-D01-Combate-03-Menu.zip](builds/Doom-D01-Combate-03-Menu.zip?raw=true) · [Comparar toda a branch com a base do Cláudio](https://github.com/bollux78/MD-DOOM64KB/compare/fa5339e69e4e2dd5f8fe6a088f1a3c5fadb8ccba...exp-dread-md-d01-werk) · [Instruções de build](tools/BUILD-MAPS.md)

Na abertura, START, A, B ou C mostram o menu. **New Game** entra em E1M1, **Select Level** lista E1M1–E1M9 pelo nome e **Benchmark** executa o percurso fixo de E1M1. Durante o jogo, A dispara, B opera portas compatíveis e START abre a pausa do D01.

## Histórico

| Commit | O que entrou |
| --- | --- |
| [8a7d458](https://github.com/bollux78/MD-DOOM64KB/commit/8a7d4588dded5fa575a276c3d3a4e969f4a8b7cb) | Conversor com setores de 16 bits, builds por mapa e suporte a testes de geometria. Foram abertas em emulador as 18 ROMs individuais de Doom shareware e Freedoom Phase 1 E1M1–E1M9. |
| [59ec940](https://github.com/bollux78/MD-DOOM64KB/commit/59ec940c760fad08f490987c2af4033b8cfa341d) | Nove fases na mesma ROM, colunas de textura e dados de sprites deduplicados, PVS compactado por linha, dicionário de tiles do HUD e da pistola, introdução e nove músicas XGM2. |
| [feff31b](https://github.com/bollux78/MD-DOOM64KB/commit/feff31b40372d7248e508a279b6ea8f8509acfd4) | Combate opcional com setores e recorte do D01, monstros que acordam, perseguem e causam dano, pistola que acerta o primeiro alvo visível. |
| [c85afd2](https://github.com/bollux78/MD-DOOM64KB/commit/c85afd2f6b90e081569c0d81729d33ba413b0a8a) | Combate 02. Restaurou o incremento de 2 bytes do VDP antes de carregar as paletas, tiles e tabela de sprites da interface. |
| [2aecba2](https://github.com/bollux78/MD-DOOM64KB/commit/2aecba2ee07f3a8018830876d1353d23b376514b) | Combate 03. Restaurou a arte de abertura do Bollux, com texto branco e fundo escurecido no menu inspirado na R128. |

## Validação

- **Combate 03 no Genesis Plus GX.** Menu, abertura das nove fases, HUD, pausa, mudança de H40 para H32 e retorno ao jogo. No encontro controlado de E1M1, a pistola marcou seis acertos e dois abatimentos.
- **HUD e arma no BlastEm.** Na Combate 02, foram observados a pistola, o clarão do disparo e a munição de 50 para 49.
- **Benchmark de E1M1 no Genesis Plus GX (NTSC).** Foram 312 quadros no mesmo percurso. Combate 02 e Combate 03 ficaram em 3,80 FPS. A build da Combate 03 com a IA desativada ficou em 3,79 FPS.
- **Cadência no encontro controlado.** Dois atores moveram-se a cada 48 e 53 VBlanks, respectivamente, cerca de 0,8–0,9 s. A IA roda em quatro grupos e limita o deslocamento por atualização. O percurso fixo de benchmark mede o FPS naquela rota e não caracteriza todas as cenas de combate.

## Estado da build

A seleção de fases funciona na abertura. Ainda faltam transições pelas saídas, projéteis, outras armas e animações direcionais dos monstros. O episódio usa o modo de linhas duplicadas e mantém o recorte de sprites do D01. O modo de colunas está disponível nas builds antigas da base. A ROM pública deste handoff é a do Doom shareware.

```bash
GDK=/caminho/sgdk DREAD_COMBAT=1 \
  bash experiments/DREAD_MD/d01/tools/build_map.sh \
  /caminho/doom1.wad EPISODE /caminho/saida 'DREAD MD COMBAT 03'
```

SHA-256 do ZIP `6d2c20e68b1a63817240b9a593b8a9661e96b7a6e6d039647d4665c32bb88709`.
