#!/usr/bin/env python3
"""Self-contained fullscreen report for the D01 cell stream A/B experiment.
Never represents emulator speed or build success as verified game FPS."""
import json
import pathlib
import re
import sys
import html
from datetime import datetime, timezone

root=pathlib.Path(sys.argv[1])
variants=("CONTROL","CELLSTREAM")
metrics={}
for name in variants:
    log=(root/name/"mame.log").read_text(errors="replace") if (root/name/"mame.log").exists() else ""
    match=re.search(r"SPAWN_RESULT variant="+name+r" published=(\d+) vblanks=(\d+) fps=([0-9.]+)",log)
    counters=re.search(r"STREAM_RESULT variant="+name+r" rebuilds=(\d+) hits=(\d+) fallbacks=(\d+) entries=(\d+) segs=(\d+) nodes=(\d+) subs=(\d+) cols=(\d+) anchors=(\d+)",log)
    metrics[name]=dict(
        measured=bool(match),
        published=int(match[1]) if match else None,
        vblanks=int(match[2]) if match else None,
        fps=float(match[3]) if match else None,
        counters=dict(zip(("rebuilds","hits","fallbacks","entries","segs","nodes","subs","cols","anchors"),map(int,counters.groups()))) if counters else {},
        errors=[x.strip()[:240] for x in log.splitlines() if re.search(r"error|fatal|warning|SPAWN_BEGIN",x,re.I)][:18],
    )
c,b=metrics.values()
gain=100*(b["fps"]/c["fps"]-1) if c["fps"] and b["fps"] else None
sha=(root/"SHA256SUMS.txt").read_text(errors="replace") if (root/"SHA256SUMS.txt").exists() else "Not available"
timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
payload={"generated":timestamp,"variants":metrics,"gain_percent":gain,"visual_verified":False,"sha256":sha}
(root/"benchmark.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False))
def fmt(n, suffix=""):
    return ("Não medido" if n is None else f"{n:.4f}{suffix}" if isinstance(n,float) else f"{n}{suffix}")
def card(name,title):
    m=metrics[name]
    return f'<section class="card"><p class="eyebrow">{html.escape(title)}</p><strong class="big">{fmt(m["fps"])} <small>FPS</small></strong><p>{fmt(m["published"])} publicações · {fmt(m["vblanks"])} VBlanks</p><p class="muted">MAME NTSC · 1.200 VBlanks · spawn E1M1</p></section>'
def row(label,key):
    a,b=metrics["CONTROL"]["counters"],metrics["CELLSTREAM"]["counters"]
    return f"<tr><th>{html.escape(label)}</th><td>{a.get(key,'—')}</td><td>{b.get(key,'—')}</td></tr>"
notes="As taxas são publicações completas no VDP, não FPS do emulador. As métricas da cena são amostras do último quadro, não médias. O framebuffer NÃO foi comparado pixel a pixel. O stream não implementa diretamente o formato binário da Ferret: aproveita o princípio de lista de visibilidade ordenada, derivada do BSP/PVS da D01, com cache por posição. A condição por posição é necessária para preservar a ordem de oclusão. A mudança de câmera invalida o cache. Portas, inimigos, HUD, música, START, nove mapas e quatro modos gráficos exigem teste de regressão no hardware."
diag=""
for name in variants:
    lines=metrics[name]["errors"]
    diag+=f"<details><summary>{name}: eventos do log ({len(lines)})</summary><pre>{html.escape(chr(10).join(lines) or 'Nenhum evento selecionado')}</pre></details>"
report=f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOOM MD · CellStream B1 · Benchmark</title>
<style>
:root{{color-scheme:dark;font-family:Inter,system-ui,Arial;background:#090b12;color:#f3f4f9}}
*{{box-sizing:border-box}}body{{margin:0}}main{{padding:24px 3vw 65px;min-height:100vh;max-width:1800px;margin:auto}}
header{{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;border-bottom:1px solid #303646;padding-bottom:20px}}
h1{{font-size:clamp(26px,3vw,48px);margin:4px 0}}h2{{font-size:20px}}.eyebrow{{color:#a8bedf;text-transform:uppercase;letter-spacing:.12em;font-size:12px}}
.muted{{color:#a2adbf;font-size:13px}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:20px 0}}
.card{{background:#151a29;border:1px solid #30394b;border-radius:14px;padding:22px;min-width:0}}
.big{{font-size:clamp(29px,3.8vw,56px);letter-spacing:-.05em}}small{{font-size:14px;letter-spacing:0}}
.positive{{color:#85e2a1}}.negative{{color:#ff9a9a}}.warning{{color:#ffd288}}
.columns{{display:grid;grid-template-columns:1.1fr 1fr;gap:18px}}table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}
th,td{{padding:10px 9px;border-bottom:1px solid #30394b;text-align:right}}th:first-child{{text-align:left}}thead th{{color:#b9cae3}}
.banner{{border-left:4px solid #f7c86a;padding:13px 18px;background:#242131;margin-top:18px}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;color:#b8c5de}}details{{margin:8px 0;border:1px solid #313748;padding:10px 14px;border-radius:8px}}
summary{{cursor:pointer}}a{{color:#b9d4ff}}code{{font-size:12px}}.bar{{height:18px;background:#293344;border-radius:10px;margin:14px 0;overflow:hidden}}
.bar>span{{display:block;height:100%;background:#69afda}}.bar.green>span{{background:#78d6a4}}
@media(max-width:1000px){{.grid{{grid-template-columns:1fr}}.columns{{grid-template-columns:1fr}}}}
</style></head><body><main>
<header><div><div class="eyebrow">DREAD D01 · Pesquisa Ferret · B1 experimental</div>
<h1>Renderer · Relatório completo</h1><div class="muted">{timestamp} · MAME / Mega Drive NTSC · 59,922743 Hz</div></div>
<div><strong class="warning">VALIDAÇÃO VISUAL PENDENTE</strong><p class="muted">Não publicar como otimização aprovada</p></div></header>
<div class="grid">{card("CONTROL","Referência sem cache")}{card("CELLSTREAM","PVS + stream por posição")}
<section class="card"><p class="eyebrow">Ganho comparável</p><strong class="big {'positive' if gain is not None and gain>0 else 'negative' if gain is not None and gain<0 else ''}">{fmt(gain,'%')}</strong><p class="muted">Calculado de publicações reais, mesma janela NTSC</p></section></div>
<div class="columns">
<section class="card"><h2>Comparação do renderer</h2>
<div class="eyebrow">FPS do jogo · Não confundir com velocidade da emulação</div>
<p>CONTROL {fmt(c['fps'])} FPS</p><div class="bar"><span style="width:{min(100,(c['fps'] or 0)/12*100):.1f}%"></span></div>
<p>CELLSTREAM {fmt(b['fps'])} FPS</p><div class="bar green"><span style="width:{min(100,(b['fps'] or 0)/12*100):.1f}%"></span></div>
<h2>Estatísticas de execução</h2><table><thead><tr><th>Indicador</th><th>CONTROL</th><th>CELLSTREAM</th></tr></thead><tbody>
{row("Streams reconstruídos","rebuilds")}{row("Reutilizações do stream","hits")}{row("Fallback ao BSP","fallbacks")}
{row("Subsectors no stream","entries")}{row("Segmentos desenhados (último quadro)","segs")}
{row("Nós BSP visitados (último quadro)","nodes")}{row("Subsectors visitados (último quadro)","subs")}
{row("Visitas a colunas","cols")}{row("Âncoras de projeção","anchors")}</tbody></table>
<p class="muted">Métricas do stream são cumulativas; estatísticas de cena representam a última amostra e não médias.</p></section>
<section class="card"><h2>Integridade e condições</h2>
<p><strong class="warning">Equivalência visual:</strong> não verificada automaticamente nesta execução.</p>
<p><strong>Comparação:</strong> mesmo WAD shareware, código da mesma branch, flags idênticas exceto <code>-DDREAD_CELL_STREAM</code>.</p>
<p><strong>Janela:</strong> VBlank 1200 até 2400, contagem de frames publicados após DMA e flip completo.</p>
<p><strong>Hardware:</strong> MAME Mega Drive, modo NTSC, sem SRAM adicional requerida.</p>
<p><strong>Funcionalidade:</strong> versão completa E1M1–E1M9. Testes de gameplay permanecem pendentes.</p>
<p class="banner">{html.escape(notes)}</p>
<h2>SHA-256 das ROMs</h2><pre>{html.escape(sha)}</pre><h2>Diagnóstico do emulador</h2>{diag}
</section></div>
<section class="card"><h2>Próximas validações obrigatórias</h2>
<p>1. Capturas sincronizadas CONTROL × CELLSTREAM no spawn e em ângulos extremos. 2. Passeio e portas, atores, START e quatro modos gráficos. 3. Repetições e análise de custo de rebuild vs cache. 4. Perfil separado de PVS/BSP, setup, texel loop e DMA antes de decisões arquiteturais.</p>
<p class="muted">Artefatos gerados: benchmark.html, benchmark.json, ROMs, hashes, logs e build logs. Os resultados não equivalem à validação de pixels.</p></section>
</main></body></html>"""
(root/"benchmark.html").write_text(report)
print("REPORT_RESULT "+json.dumps({"control_fps":c["fps"],"stream_fps":b["fps"],"gain_percent":gain,"visual_verified":False}))
