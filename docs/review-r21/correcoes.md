# Integração do pacote de revisão R21

Patches independentes recebidos do usuário (11 commits) aplicados à fonte exata8d875327922a7f6bedd3142dbafda02d628c4fbd. Não se implementaram mudanças de resolução nesta rodada.

Correções locais antes do build:

- Modelo deheap passa a ler flags de cadaROM:inclui2128B+header da alocaçãoV2c, fila/bufferS5 e remoção da exigência de fonte ao fim comF1; exigência no boot continua obrigatória.
- As sondas deliberadas exigem a falha esperada no estágio correto. Uma exceção de sonda não desliga as verificações das demaisROMs.
- Auditoria de layout aceita opçõesR21 como experimentos e continua comparando as outras flags.
- S5 usa capacidade65535(-1), que oSGDKcb114ac define como ilimitada;0 era limitezero. Isso vale emprobe-s5 e f1-s5, não altera a base semS5.
- PredicadoN4 usa soma explicitamenteunsigned antes de reinterpretar a fração, evitando novo overflowassinado. Testehost usa a mesma expressão e multiplicação no lugar de deslocamento de negativos. Executado comUBSan,2.213.484.800casos,zerodivergências.
- Quatro diagnósticos extras:diag-n3,diag-n4,diag-f1,diag-f1-s5. Matriz final24ROMs,nomes≤30caracteres.
- PicoPLAY é watermark repintado no início daDEMO3;SPmínimo continua desdeboot. Não confundir as duas medidas.

O modelo é específico do layout doSGDKusado:fonte96tiles APLib,memóriaalta0xE0FFF600,pilha2560,fila80×16,bufferpadrão8192. ACI incluiheaders exatos e identidade doSDK para conferência. Não substitui diagnóstico de fragmentação/runtime.
