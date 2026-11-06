# DOOM SCD — Benchmark 03B

Diagnóstico de boot do segundo 68000 em **Sega CD Mode 1**. O Mega Drive inicia pelo cartucho, carrega um programa de teste na Program RAM e verifica que o sub-CPU responde a desafios de 16 bits.

## Compilar no CachyOS

Extraia o ZIP e rode na pasta do projeto.

```fish
cd ~/Projetos/DOOM_SCD_Bench03B
fish build.fish
```

O caminho padrão do SGDK é `/home/dan/mars/m68k-elf`. Para outra instalação, use `env GDK=/caminho/do/sgdk fish build.fish`. Abra **`build/doom-scd-bench03b.bin`**, a ROM com o indicador de suporte ao Sega CD no cabeçalho.

## Validar no Kega Fusion

Use a mesma configuração do 03A com Sega CD conectado e boot pelo cartucho. Este teste executa sem dados de disco.

- `BOOT SEQUENCE: OK` confirma a cópia, a releitura do programa na Program RAM e a liberação do sub-CPU.
- `SUB SIGNATURE: SC (READY)` exige uma assinatura válida e avanço do heartbeat.
- `COMMANDS OK` deve subir, `ERRORS` deve ficar em zero e `BEAT CHANGES` deve subir.
- Se falhar, envie uma captura da tela. Ela identifica se a falha ocorreu na detecção, no reset, na solicitação de barramento, na Program RAM, na liberação ou no ACK.

O 03B testa Program RAM e registradores de comunicação. A etapa 03C fica para depois da confirmação do 03B e vai medir a troca de buffers pela Word RAM.

[Sequência de boot em Mode 1](https://www.plutiedev.com/subcpu-in-mode1)
