# Teste A de SRAM — E1M1, E1M2 e E1M8

Base do Cláudio **dc3e1de**, depois da mudança de setores para ROM.
As quatro ROMs têm **1.966.080 bytes (1,875 MiB)**, incluindo os três mapas,
céu, sprites e combate da base. A música e a arte de abertura foram
dispensadas pelo modo de teste.

O SGDK faz SRAM_disable no boot. O teste chama SRAM_enable uma única vez
antes da sondagem e mantém a janela ativa, com toda a ROM abaixo de 0x200000.
Essa habilitação do controle SRAM em A130F1 é necessária nesta versão do SGDK.
O teste A não alterna a janela com dados de ROM durante o jogo.

A sondagem grava e lê 0x55AA e 0xA55A como palavras e restaura a palavra original.
AUTO só escolhe SRAM se ambas forem lidas integralmente. CONTROL registra
o resultado da sondagem e força WRAM.

## Resultados no Genesis Plus GX

| Cenário | Linhas WRAM | Linhas SRAM16 | Colunas WRAM | Colunas SRAM16 |
| --- | ---: | ---: | ---: | ---: |
| E1M1, percurso fixo de 312 quadros | 3,526 FPS | 3,526 FPS | 3,882 FPS | 4,692 FPS |
| E1M1, câmera e atores parados | 3,392 FPS | 3,392 FPS | 4,000 FPS | 4,775 FPS |
| Começo E1M2, giro à esquerda por 300 VBlanks | 4,889 FPS | 4,889 FPS | 4,719 FPS | 6,084 FPS |

O benchmark de E1M1 teve 5.309 VBlanks em linhas, 4.822 em colunas WRAM e
3.990 em colunas SRAM16. Ganho de **20,85%** em colunas. A cena parada
confirmou um ganho de **19,38%**, com SHA-256 idêntico do viewport dentro de
cada modo. No giro de E1M2 há IA ativa, e a evolução das poses pode divergir
com o FPS. Esse cenário teve 28,92% de ganho em colunas.

Cada cenário foi repetido com SRAM16, sem SRAM e com SRAM8 no byte ímpar.
Ausência e 8 bits escolheram WRAM, registraram zero acessos à SRAM em jogo
e produziram os mesmos totais de VBlanks no benchmark do controle.
O rótulo N1/N2 mostra os buffers de CPU. As ROMs AUTO em linhas continuam
usando dois, e AUTO em colunas passa de um para dois quando detecta SRAM16.

O modo colunas conserva um único buffer na VRAM. Duas cópias de 23.040 bytes
atingiriam o HUD e as tabelas do VDP. Separar a quantidade de buffers de CPU
da quantidade de cópias VRAM foi necessário para testar a proposta sem
corromper a imagem.

Também foi corrigida uma tela preta na troca de linhas para colunas.
O VBlank do modo linhas pode deixar o display desligado, à espera do H-int.
set_mode agora religa o display antes de escolher o próximo modo.

## Validação e reprodução

- 36 verificações de gameplay — quatro ROMs, três condições SRAM, três mapas.
- Tiro, troca de modo e retorno da pausa verificados.
- 12 benchmarks de 312 quadros, com limitador desligado pelo próprio benchmark.
- 12 medições de câmera parada e 12 giros de E1M2.
- Falta teste em console físico, com a largura de SRAM efetivamente oferecida
  pelo EverDrive X7.
- O teste B de episódio completo com troca de janela fica para outra rodada.
  Este pacote atende aos três mapas escolhidos para o teste A.

O patch do emulador em tools/sram_gpgx.patch foi aplicado ao Genesis Plus GX
2499cd3e3d1d8b7d0130d8b2825adb4cc608b2c0. Ele registra DMA e escritas no
registro 2 do VDP e permite SRAM ausente ou de 8 bits. Não altera o custo
de ciclos das instruções do 68000. O perfil foi executado em NTSC sem Sega CD.

```sh
git apply /caminho/tools/sram_gpgx.patch
make -f Makefile.libretro HAVE_CHD=0 -j6
python3 /caminho/tools/verify_sram.py \
  --core ./genesis_plus_gx_libretro.so \
  --builds /caminho/builds \
  --out /caminho/resultados \
  --scenario bench --nm m68k-elf-nm
```

As pastas de build esperadas são auto-lines, control-lines, auto-columns e
control-columns, cada uma com EPISODE.bin e seu EPISODE.elf local.
Os cenários fixed, turn e smoke usam os mesmos argumentos.
Os JSONs e hashes estão no ZIP das ROMs.
