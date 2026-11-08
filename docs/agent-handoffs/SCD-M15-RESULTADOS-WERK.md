# M1.5 — resultado do Werk

Data: 2026-11-08. Branch: `exp-werk-scd-subport-s1s2`.
Implementação validada: `a2db2a189ceeec580b87cc66a9e5e798df2a533d`.

**build: PASS. blastem: PASS. Console físico: pendente.**

Evidência: [run 42510382581](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42510382581), job `128821952844`. Os dois veredictos constam separadamente no log; o workflow falha se qualquer teste falhar. Tentativas anteriores com FPS insuficiente, descarte ou dívida excessiva foram rejeitadas.

## Resultados

| Medida | Modo de uso, roteiro principal | Percurso porta/item/tiro |
| --- | ---: | ---: |
| Apresentação | **5,0104 FPS** | 7,44 FPS |
| Lógica pelo relógio independente do MD | **34,8225 Hz** | 34,944 Hz |
| Tics descartados | **0** | **0** |
| Dívida de relógio no fim / máxima observada | 1 / 2 tics | 1 / 2 tics |
| Maior intervalo de leitura do relógio | 32,10 ms | 30,41 ms |
| Demanda até banco, média / máximo | 5,10 / 30,78 ms | 3,50 / 18,34 ms |
| Aplicação do mundo, média | 4,79 ms | 5,11 ms |
| Aplicação de atores + jogador, média | 10,51 ms | 10,11 ms |
| Aplicação total, média | 15,30 ms (~0,918 VBlank) | 15,22 ms |
| Proxy / jogador, média | 9,84 / 0,67 ms | 9,31 / 0,80 ms |
| Validação/cabeçalho/backups, média | 6,06 ms | 6,37 ms |
| Captura completa no sub, média / máximo | 25,64 / 29,03 ms | 25,26 / 28,66 ms |
| Captura: mundo / atores / cópia+checksum | 13,91 / 8,02 / 3,52 ms | 13,85 / 7,75 / 3,47 ms |
| Tic, custo médio | 13,51 ms | 12,22 ms |
| Maior idade do snapshot entregue | **4 tics** | **8 tics** |

A meta principal de >4,6 FPS passou no roteiro de uso: aproximadamente +8,9% sobre essa referência, e +40,7% sobre os 3,56 FPS publicados do M01. São medidas em tempo emulado do BlastEm, não FPS medidos no console. O roteiro usa comandos por quadro entregue, como o M01: ao mudar o FPS, muda o tempo de cada comando e a trajetória resultante. Não é uma comparação de imagens/estados idênticos nem uma demonstração de raster mais rápido.

M0: 24 quadros com câmera congelada, razão de custo CD/nativo **1,00128**. Raster e conversão R128 não foram alterados.

Os alvos secundários de demanda <1 ms e aplicação total <=10 ms **não foram atingidos**. A captura nominal a cada dois tics custa ~12,82 ms/tic; somada ao tic médio dá ~26,33 ms/tic, abaixo de 28,57 ms, mas acima da folga desejada de 22 ms. Picos exigem recuperação.

## Implementação

- Snapshot previamente montado e checksum de payload previamente calculado. Na demanda, o sub sela cabeçalho/eco e troca o banco. A entrega pode ocorrer dentro das leituras do relógio durante lógica/captura, usando somente um pacote completo e imutável.
- WAD síncrono tem trava de transporte; a entrega assíncrona não usa os registradores enquanto esse transporte está ocupado.
- Captura nominal a cada dois tics. Durante recuperação, evita recapturar um snapshot ainda preparado e não solicitado; prioriza executar a dívida, sem descartar tics. A idade visual aumenta temporariamente: até 8 tics (~229 ms) observados no percurso. Este é um desvio explícito da previsão inicial de idade de apenas 1 tic.
- O limite de recuperação executa até 8 tics por lote, carregando o restante para o lote seguinte. Overflow do acumulador falha explicitamente. O teste continua exigindo 35 Hz ±2%, zero descartes e dívida final <=8; não basta zerar o contador de descartes.
- Relevância de apresentação: jogador sempre presente; demais objetos com sprite válido e até 1.280 unidades em cada eixo. Não há filtro de visão/oclusão; atores atrás da porta continuam presentes. A simulação completa permanece no sub.
- Registros compactos de 24 bytes: XYZ 16.16, ângulo de 8 bits, flags compactadas, sprite/frame/setor de 16 bits e ID estável. A câmera real do jogador mantém o ângulo completo.
- Proxies persistentes por banco; mudança de setor/NOSECTOR, criação e remoção refazem os vínculos necessários. Objetos que continuam no mesmo setor mantêm os vínculos.
- Aplicação diretamente do pacote validado em Word RAM; não há cópias intermediárias de mundo/atores.
- Deltas usam conjunto conservador acumulado de registros que já mudaram: pode reenviar registros, mas não perde transições A->B->A entre capturas/entregas. Primeira entrega completa.
- Hash semântico do mundo atualizado por registro; checksum completo de payload e cabeçalho preservados. O MD mantém auditoria semântica profunda em todos os quadros do modo deep e a cada 32 no uso.
- No uso, evita serializar um segundo espelho de diagnóstico quando não há hash nativo profundo. O teste externo continua lendo e comparando os campos dos próprios objetos nativos em **todos** os quadros.
- Verificação dos vínculos de todas as listas de setor continua a cada quadro. As únicas unidades MD com otimização O3 adicional são aplicação de mundo/atores e transporte/orquestração; nenhum arquivo de raster/conversão foi modificado.
- S2e/M01 e trabalho N2/M2 do Cláudio preservados; alterações compartilhadas condicionadas a SCD_M15.

## Validação executada

1. Produtor C real do mundo compilado no host: **400 casos PASS**, incluindo A->B->A e entrega durante captura; comparação de estado reconstruído e hash incremental com recomputação completa.
2. Build/link estrito e ROM Mode 1: PASS.
3. M0 congelado: PASS, custo de raster equivalente ao controle.
4. Roteiro profundo: PASS, **34,7697 Hz**, zero descartes, todas as auditorias.
5. Roteiro de uso: PASS, **5,0104 FPS**, 34,8225 Hz, zero descartes.
6. Percurso com comandos de controle, sem teleportar: PASS. Pegou item, abriu e atravessou porta, disparou, reteve o inimigo do outro lado da geometria.
7. Checksums, reconstrução de deltas, IDs/campos nativos, vínculos das listas, estado do jogador/HUD/PSprites, eco do controle, alternância dos dois bancos, ausência de simulação MD e retorno/restauração normal: PASS.

O teste automatizado confirma a retenção do ator encoberto e os estados nativos; a aparência da oclusão deve ser inspecionada no teste físico.

## ROM para testar

Arquivo privado já gerado no computador do Daniel:

```text
/home/dan/Projetos/Personal/scd-subport-m15/run-42510382581-1/doom-md-scd-m15.bin
```

ELF, relatórios `live_deep_report.json`, `live_report.json`, `route_report.json` e quadros de diagnóstico ficam nessa pasta. A ROM tem **4.063.232 bytes**. Nenhum binário, WAD ou imagem do jogo foi publicado no GitHub.

Inicializar como as ROMs Mode 1 anteriores, com Sega CD conectado; **START** entra no jogo. Conferir movimento, giro, tiro, porta, item e sprites parcialmente encobertos, especialmente durante picos de movimento/abertura de porta. Comparar a sensação de atraso visual com M01. Aprovação no BlastEm não substitui essa verificação no hardware.

## Arquivos / reprodução

Fontes e testes: `experiments/DOOM_SCD_SubPort/m15/`.
Workflow: `.github/workflows/scd-subport-m15-iterate.yml`, gatilho de commit `[m15-iterate]`.

O workflow usa cópia descartável de R128 com objetos-base conhecidos, assets privados locais e configuração isolada do BlastEm em divisor 7. Não altera o checkout original do usuário. Código compartilhado relevante: `s1d/build_setup.py`, `s1e/engine_build.py`, `s2b/world_values.h`, transportes MD/sub e a exclusão do gatilho M15 no workflow S2e.

Prioridade seguinte, se a ROM passar no console: reduzir custo de captura/mundo e latência de resposta; não alterar o renderer para atribuir ganhos a esta etapa.
