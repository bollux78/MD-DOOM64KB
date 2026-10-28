# Pedido ao agente: analisar e implementar otimizações de desempenho

Você pode analisar e implementar candidatos neste projeto. Comece por `docs/performance-r80/PROJETO.md` e pelo README desta pasta.

O alvo é a R79 base, sem shadow adaptativo: 7,32 FPS médios no DEMO3 completo enviado pelo usuário. Preservar clock, imagem, áudio, lógica, HUD e menus. Save/load, fontes e novos efeitos de shadow estão fora desta tarefa.

O repositório completo está neste branch. Fontes preparados para leitura, flags reais e instruções de acesso a ROMs/ELFs de controle estão nesta pasta. Há um hook de candidato inerte em `scripts/lab/apply_r80_performance.py`, uma preparação de apenas controle/candidato e um workflow com acionamento explícito. Crie um branch `exp-seuagente-r80-descricao` a partir daqui.

Primeiro confronte as hipóteses com os flags e o ELF atuais. MOVEP, MUL ASM, COLPAIR, locais/invariantes e várias LUTs já estão ativos. O perfil R71 é histórico. Priorize até três mudanças fundamentadas e comece por uma alteração pequena e isolada. Pode rejeitar ou modificar as sugestões do projeto.

Implemente no hook R80 após a cadeia R79; evite modificar a base original ou os patches históricos. Acrescente testes de equivalência, preserve os fallbacks e forneça resultados reais. Inicie o workflow apenas quando o candidato e os testes estiverem prontos. O hook inicial vazio não é uma otimização.

Limites: BSS ≤57.920 bytes (o PLAY tem só 10 bytes de folga), ROM ≤4 MiB, automação BlastEm ≤10.000 frames por execução. O smoke de 800 frames não substitui benchmark completo. Não contornar o limite com sessões sequenciais para alegar execução completa. Não promover uma mudança baseada apenas em amostra curta ou estimativa.

Devolva: diagnóstico, propostas apoiadas/rejeitadas com evidências, commit do candidato, alterações de memória, testes de equivalência e resultados/limites da medição. Se não conseguir executar algo, diga explicitamente. Preserve o branch de referência e não faça merge na base aceita.
