"""One local review with original captions and bidirectional reference links."""
import html
import json


def write_page(out, summary, panels, targets, sharma):
    esc = html.escape
    image = lambda name: f'<a href="{name}.png"><img src="{name}.png" loading="lazy" alt="{esc(name)}"></a>'
    body = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>G2 preliminary comparison</title><style>
body{margin:0;background:#f7f6f1;color:#26312c;font:16px/1.65 system-ui,sans-serif}main{max-width:1320px;margin:auto;padding:30px 28px 70px}
h1{font-size:2.5rem;line-height:1.15}h2{font-size:1.45rem}section{border-top:1px solid #d2d7cc;padding:26px 0}.pair{display:grid;grid-template-columns:1.2fr 1fr;gap:22px;align-items:start}
img{width:100%;height:auto;background:white}a{color:#00687b}.warning{background:#fff0df;border-left:5px solid #a55a27;padding:15px 20px}
.caption{font-size:.92rem}code{overflow-wrap:anywhere}details{padding:10px;background:#eef0e9}pre{white-space:pre-wrap;font-size:.82rem}
nav{display:flex;gap:18px;flex-wrap:wrap;margin:25px 0}@media(max-width:760px){.pair{grid-template-columns:1fr}main{padding:20px 14px}}
</style><main><p>M4 / M5 · RETAINED DEVELOPMENT EVIDENCE</p><h1>G2: the first reacting transient</h1>'''
    body += f'<p>{esc(summary["label"])}. Saved sample times: {esc(", ".join(f"{t*1e6:g} μs" for t in summary["times_s"]))}.</p>'
    body += '<div class="warning"><b>Preliminary startup diagnostic.</b> Paper curves are long-time statistics; these fields are instantaneous. No developed flame, LES, scientific acceptance or optical calibration is claimed. Missing statistics remain missing.</div>'
    body += f'<p>Our x = mesh x − {summary["x_origin_m"]:g} m. {esc(summary["origin_note"])}. The 10k co-planar wedge omits the upstream taper and chamber corners.</p>'
    body += '<nav>' + ''.join(f'<a href="#{p["name"]}">{esc(p["title"])}</a>' for p in panels) + '<a href="#references">References</a></nav>'
    for panel in panels:
        ref = panel.get('reference')
        body += f'<section id="{panel["name"]}"><h2>{esc(panel["title"])}</h2><p>{esc(panel["meaning"])}</p>'
        if ref:
            target = targets[ref]
            body += '<div class="pair"><div>'+image(panel['name'])+'</div><div>'+image('original-'+ref)
            body += f'<p class="caption">{esc(target["original_caption"])}</p><p><a href="#ref-{ref}">Paper and comparison contract</a></p></div></div>'
        elif panel['name'].startswith('axial-'):
            body += '<div class="pair"><div>'+image(panel['name'])+'</div><div>'+image('original-figure4b')
            body += f'<p class="caption">{esc(sharma["caption"])}</p><p>The crop is panel b. Gray shading marks experimental flame location.</p><a href="#ref-sharma4b">Paper</a></div></div>'
        else:
            body += image(panel['name'])
        body += '</section>'
    body += '<section><h2>Missing data and qualifications</h2><ul>' + ''.join(f'<li>{esc(item)}</li>' for item in summary['limitations']) + '</ul>'
    body += '<p>No CFD RMS is inferred from a few saved snapshots. Schmitt Figure 21 is retained as a reference target; its velocity/oxygen profiles and 83/300 K conditions have no equivalent comparison in this render.</p>'
    body += '<details><summary>Declared runtime identity and case inputs</summary><pre>'+esc(json.dumps({'run':summary['run_identity'],'case':summary['case_conditions']},indent=2))+'</pre></details></section>'
    body += '<section id="references"><h2>References and original captions</h2>'
    for key, target in targets.items():
        paper = target['paper']
        body += f'<section id="ref-{key}"><h3>{esc(paper["short"])}</h3><p><a href="{esc(paper["url"])}">{esc(paper["title"])}</a></p><p class="caption">{esc(target["original_caption"])}</p>'
        body += '<p>Return to: '+' | '.join(f'<a href="#{p["name"]}">{esc(p["title"])}</a>' for p in panels if p.get('reference')==key)+'</p>'
        body += '<details><summary>Original figure and comparison definition</summary>'+image('original-'+key)+'<pre>'+esc(json.dumps(target['plot_spec'],indent=2))+'</pre></details></section>'
    body += f'<section id="ref-sharma4b"><h3>Sharma Figure 4b</h3><p><a href="{sharma["url"]}">{esc(sharma["paper"])}</a></p><p>{esc(sharma["caption"])}</p><a href="#axial-instantaneous">Return to near-axis comparison</a></section>'
    body += '<p><a href="receipt.json">Input, source and artifact hashes</a> · <a href="data/">Consumed sample CSVs</a>. No solver execution or publication by this renderer.</p></section></main></html>'
    (out/'index.html').write_text(body,encoding='utf-8')
