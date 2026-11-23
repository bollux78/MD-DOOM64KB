# Padrão de benchmark para os projetos Doom: DEMO3 / E1M7

**Decisão do projeto (23/11/2026):** adotar a **DEMO3 original do Doom 1 shareware, em E1M7 (Computer Station)** como benchmark de referência nas ROMs e nos futuros experimentos Doom. Este é o benchmark **padrão**, tanto para a R128 quanto para a DREAD C7 e novos ports, quando o replay for compatível.

## Protocolo canônico

1. Usar o **lump `DEMO3` do mesmo Doom 1 shareware de referência**, sem recriar a rota com comandos inventados e **sem forçar E1M1**. Conferir no cabeçalho da demo o episódio e o mapa: o padrão exige E1M7.
2. Reproduzir a **gravação completa**, até o marcador de fim; combate, portas, tiros, movimentação e eventos ficam sob controle dos comandos originais. Não comparar uma versão de 312 quadros com a demo integral como se fossem o mesmo teste.
3. Medir **VBlanks de vídeo NTSC** entre o início e o término, incluindo renderização e lógica. Calcular tempo total e FPS com a mesma definição em todas as variantes. Usar VBlanks reais, não velocidade da máquina hospedeira nem tempo de compilação.
4. Relatório na ROM: **nome da ROM**, **identificação da variante**, `DEMO3 / E1M7 / NTSC`, **FPS médio**, **mínimo e máximo por janelas de 1 s**, **quadros renderizados**, **VBlanks totais** e **tempo total em segundos**. Para depuração e regressões, registrar também o **histograma de VBlanks por quadro**.
5. Relatório externo: SHA-256 da **ROM**, identidade/hash do WAD de entrada e do lump DEMO3, commit, versão do emulador/hardware, configuração de vídeo e número de repetições.
6. Repetir no mínimo duas vezes por configuração; usar a mesma ROM, WAD, dificuldade e ambiente ao comparar alterações. **Não alterar a jogabilidade apenas para melhorar o FPS do benchmark.**

## Interpretar com cuidado

- O padrão é um **cenário de teste compartilhado**, não garantia de equivalência entre engines. Demos clássicas registram entradas, não uma captura de vídeo; física, colisão, IA, RNG e cadência de atualização diferentes podem dessicronizar o replay.
- Na DREAD C7 atual, a reprodução converte os ticcmds do Doom para a física própria do port. **Ainda requer validação visual e de eventos** (trajeto, portas, tiros e encontros). Até isso ocorrer, não chamar seu tempo/FPS de comparação exata com a R128.
- Diferenciar no relatório: **DEMO3 canônica completa E1M7**, **trecho de smoke test** e **replay aproximado**. O teste sintético anterior de rota fixa E1M1 está aposentado para ROMs C7.
- Se um projeto não puder reproduzir E1M7, registrar a limitação e usar outro teste **com rótulo diferente**; nunca apresentá-lo como o padrão DEMO3 E1M7.

## Distribuição e reprodução

- O build extrai DEMO3 do **WAD local**. Não publicar o WAD ou ELF nos artefatos. Entregar ROMs de teste em ZIP e hashes.
- Por padrão, **BENCHMARK** no menu deve executar essa demo integral e apresentar a tela de resultados; não manter implementações redundantes de benchmark em ROM sem necessidade.
- O teste curto automatizado pode existir como verificação rápida de CI, mas seu nome e resultados precisam distingui-lo explicitamente do benchmark padrão.
