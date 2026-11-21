# Dread D01 — testes de linhas, colunas e detalhe completo

As seis ROMs têm E1M1–E1M9 do Doom shareware, música, menu, HUD, pistola e a lógica atual de combate. Cada ROM ocupa 3,375 MiB, com cartucho padrão. O ponto de partida é o commit ceab10436f06b649eba6b9c322c491ebd0d3c389 da branch exp-dread-md-d01-claudio.

## Como comparar

Use Benchmark no menu inicial. As ROMs executam o mesmo percurso de 312 quadros em E1M1, com o detalhe indicado no nome do arquivo. Em jogo, START abre os ajustes. TELA alterna H40/H32. DETALHE alterna MEIA VERTICAL, MEIA HORIZONTAL e COMPLETO. O limitador pode ser colocado em LIVRE.

| ROM | Detalhe inicial | Benchmark NTSC no Genesis Plus GX |
| --- | --- | --- |
| 01-Controle-Minimo.bin | Meia vertical, H-int incremental | 3,631 FPS |
| 02-Linhas-Robusto.bin | Meia vertical, H-int com cálculo pelo contador | 3,512 FPS |
| 03-Linhas-Tabela.bin | Meia vertical, H-int com tabela de 512 bytes | 3,592 FPS |
| 04-Linhas-Sem-HInt.bin | Meia vertical, expansão em assembly antes do DMA | 3,804 FPS |
| 05-Completo.bin | Altura completa, sem duplicação de linhas | 3,101 FPS |
| 06-Meia-Horizontal.bin | Meia horizontal, altura completa | 3,867 FPS |

O modo COMPLETO mantém a codificação da base em pares de duas cores. Em H40, são 160 amostras de pares por 144 linhas, formando uma imagem de 320×144 pixels. A meia vertical calcula 160×72 pares. A meia horizontal calcula 80×144 amostras e repete cada par. Os três modos ocupam o mesmo viewport.

A tabela de H-int é a implementação padrão no fonte. A ROM 04 substitui a duplicação por VSRAM pela expansão do buffer compacto, com DREAD_PACKED_ROWS. Todos os outros detalhes continuam disponíveis no seu menu.

## Validação e limites

- Os nove mapas abriram no Genesis Plus GX.
- Pausa e retorno foram verificados em H40/H32 e nos três detalhes, nas ROMs 03 e 04. A tela foi religada explicitamente em set_mode, corrigindo a troca para colunas.
- As quatro variantes de meia vertical tiveram o mesmo SHA-256 do framebuffer completo no final do benchmark. O hash é d5ac4512e3d7f23db7fa7ced52072ddd461abc1e9b78b7d3316354d6a8e1e52c. A comparação usa o buffer completo em transferência, evitando ler o buffer que o renderer está preenchendo.
- Cada variante de meia vertical foi exercitada por 2000 atualizações de vídeo andando/girando em E1M2 com IA ativa. O detector de pares ainda encontrou diferenças localizadas. A contagem bruta está em stress-results.json. As duas fases de alinhamento foram registradas porque a imagem sem H-int começa uma linha antes da imagem com H-int.
- A ROM 04 registrou zero interrupções horizontais no teste de pose fixa. Seu envio vai para um único banco de tiles e pode apresentar atualização parcial durante movimento. O alinhamento do DMA a blocos de 64 bytes preserva limites de tiles expandidos, mas o teste ainda encontrou resíduos pequenos.
- Os detalhes COMPLETO e MEIA HORIZONTAL também usam um banco de viewport na VRAM.
- As medidas do emulador usam 60 atualizações de vídeo por segundo no cálculo. Falta validação no console. Estas são ROMs experimentais.

A expansão antes do DMA envia 23.040 bytes por quadro, contra 11.520 no modo com H-int, e acrescenta 11.524 bytes de estado estático à build. A velocidade obtida com meia resolução foi aproximadamente 23–25% maior que a completa neste percurso.

## Reprodução

O arquivo build-tests.sh deve ficar na raiz do checkout ao executar. Configure GDK para o SGDK e passe o WAD shareware e o diretório de saída. O código está na branch exp-werk-dread-linhas-colunas do repositório bollux78/MD-DOOM64KB.

```bash
GDK=/caminho/sgdk bash build-tests.sh /caminho/doom1.wad /caminho/saida
```

DREAD_COPY_SEGA_S=1 foi usado nesta compilação local para o layout do SGDK instalado. A configuração de compilação dos demais recursos segue o build_map.sh do Cláudio.
