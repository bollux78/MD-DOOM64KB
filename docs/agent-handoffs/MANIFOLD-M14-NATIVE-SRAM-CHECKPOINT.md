# Manifold M14 — pausa com Continuar / Salvar / Carregar / Fases (experimento)

**Estado:** implementação em `exp-manifold-m14-native-save`. Menu/driver SRAM validados em 68000; staging e linkedição da fase E1M1 completa com SGDK no runner self-hosted **PASS** (run 44165583852, branch nativa). **A ROM final de 12 MiB ainda não foi montada e o save não foi validado no X7 real**. Não incrementar `rXXX` até aprovação.

## O que mudou

- **START em jogo:** usa novamente a pausa nativa do Manifold, sem soft reset.
- **START pausado:** continua a fase no estado atual.
- **A pausado:** salva um checkpoint persistente em SRAM.
- **B pausado:** carrega o checkpoint se pertencer à fase atualmente carregada.
- **C pausado:** reinicia no seletor de fases, como ocorria anteriormente com START.
- **B no seletor de fases:** carrega o último checkpoint e inicia automaticamente a fase salva, inclusive após desligar e religar.
- Pausa não apaga mais plano B do VDP, pois isso destruiria o HUD e o céu ao retornar.
- Apenas o código extra de polling para o menu interno do EverDrive foi removido da base. O VBlank do SGDK durante o jogo continua obrigatório; o seletor não requer IRQ de VBlank e usa polling do status do VDP.

## Dados salvos — checkpoint, não save-state

Fase E1M1–E1M9; X/Y/Z, ângulo e setor do jogador; vida, armadura, munição, armas e lista original de oito slots do inventário. O arquivo NÃO captura todo o estado dos monstros, objetos, portas, plataformas, timers, RNG nem projéteis. **Carregar depois de reiniciar inicia a fase com o mundo renovado** e restaura a situação do jogador. Carregar dentro da mesma fase restaura o jogador, mas não desfaz alterações já feitas no mundo.

## SRAM X7 em modo SSF

- `crt0.s`: cabeçalho Mega Drive alinhado explicitamente com assinatura `RA`, tipo `E020` (SRAM 16-bit não volátil), início `$2C0000` e fim `$2C00FF` em offset `$1B0`.
- `m14_sram.h`: mapeia temporariamente banco **31** do X7 em slot **5** (`$280000–$2FFFFF`), usa a metade superior desse slot em `$2C0000`, e restaura banco **5** após acesso. Código interrompe temporariamente IRQ, obtém o barramento Z80 se necessário, mantém os registros do controle e restaura as condições iniciais.
- `m14_sram.h`: dois registros alternados de 64 bytes com magic, versão, sequência, checksum e marker de commit gravado por último; leitura valida antes de restaurar.
- Flag transitória de carregamento ocupa quatro words separadas na SRAM; é consumida na inicialização da fase SGDK.
- **Restrição da arquitetura atual:** slot5 deve estar no banco 5 nas configurações da M14. Alterar o mapa de bancos exige alterar/restaurar dinamicamente seu banco original.
- SRAM em X7 e modo SSF foi documentada por Robert Hargreaves: https://blog.roberthargreaves.com/2025/03/10/sram-and-everdrives (banco31; 256KiB na metade superior do slot). Testar em hardware com ROM carregada via SD, não via USB.

## Arquivos modificados

- `experiments/DOOM_Manifold_E1M1/m01/stage_rom.py`: chama `m14_native_save.install` em vez de instalar o reboot incondicional do START.
- `experiments/DOOM_Manifold_E1M1/m01/m14_native_save.py`: aplica as alterações a `game.c`, `level.c`, `inventory.c`, `doom_statusbar.c` da fase preparada.
- `experiments/DOOM_Manifold_E1M1/tools/m14/multimap/m14_sram.h`: driver e formato de checkpoint.
- `experiments/DOOM_Manifold_E1M1/tools/m14/multimap/menu.c`: opção de carregar checkpoint ao apertar B.
- `experiments/DOOM_Manifold_E1M1/tools/m14/multimap/crt0.s`: conserta o alinhamento preexistente do cabeçalho ROM e anuncia SRAM de 16 bits.
- `.github/workflows/manifold-m14-native-save-validation.yml`: compila handler/header+menu SRAM com m68k e valida staging sem WAD privado.
- `.github/workflows/manifold-m14-native-save-private-build.yml`: compilação privada da fase E1M1 real no runner, sem publicar ROM ou WAD.

## Validação

O workflow público passou: verificou bytes do cabeçalho `RA E0 20` em `$1B0`, compilou o driver SRAM em M68000, compilou o menu bare-metal e aplicou o patch ao código real do Manifold upstream pinado. A compilação privada do mapa E1M1 real também passou após ampliar o limite fixo da BSS de `0x1F44` para `0x1F84` no linker `md_split.ld` (reserva de +64 bytes). Workflow: https://github.com/bollux78/MD-DOOM64KB/actions/runs/44165583852. O binário E1M1 fica exclusivamente no `RUNNER_TEMP`, sem upload de ROM ou WAD.

Testes ainda necessários: compilação integral SGDK do mapa; ROM completa 12MiB montada; iniciar no X7 via SD; START pausa; START retoma sem apagar HUD nem perder FPS; A salva; B recarrega; desligar/religar console; B no seletor relança a fase e restaura checkpoint; confirmar arquivo SRAM persistente no SD após trocar o jogo no menu principal.

**Não usar este ramo como versão estável antes do teste físico.** Não é suporte ao menu interno do EverDrive, que comprovadamente não funciona com o mapper SSF nesta configuração.
