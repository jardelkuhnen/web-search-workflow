import os
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone

from workflow.state import WorkflowState, RankedResult, TimelineEvent


def report_agent(state: WorkflowState) -> dict:
    print("[4/4] Report Agent        → Gerando HTML...")

    timeline_events: list[TimelineEvent] = []
    query = state["query"]
    ranked_results = state.get("ranked_results", [])
    timeline = state.get("timeline", [])

    # Generate filename
    now = datetime.now()
    filename = f"search/search_{now.strftime('%Y%m%d_%H%M%S')}.html"
    output_path = os.path.join(os.getcwd(), filename)

    html = _build_html(query, ranked_results, timeline, now)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    timeline_events.append(
        TimelineEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent="Report Agent",
            action=f"HTML gerado",
            site=None,
            query=query,
            details=output_path,
        )
    )

    # Auto-open in browser
    try:
        webbrowser.open(f"file://{os.path.abspath(output_path)}")
    except Exception:
        pass

    return {"html_path": output_path, "timeline": timeline_events}


def _score_color(score: float) -> str:
    if score >= 70:
        return "#27ae60"
    if score >= 40:
        return "#f39c12"
    return "#e74c3c"


def _build_html(
    query: str,
    results: list[RankedResult],
    timeline: list,
    generated_at: datetime,
) -> str:
    results_html = ""
    all_sites = set()

    for r in results:
        score = r["score"]
        color = _score_color(score)
        low_badge = '<span class="badge-low">baixa relevância</span>' if score < 40 else ""
        site = r.get("site") or ""
        if site:
            all_sites.add(site)
        pub = r.get("published_date") or ""
        pub_html = f'<span class="pub-date">Publicado: {pub}</span>' if pub else ""

        criteria_html = (
            f'<div class="criteria">'
            f'<span title="Relevância">Rel: <b>{r["relevance_score"]:.0f}</b></span>'
            f'<span title="Credibilidade">Cred: <b>{r["credibility_score"]:.0f}</b></span>'
            f'<span title="Recência">Rec: <b>{r["recency_score"]:.0f}</b></span>'
            f'<span title="Profundidade">Prof: <b>{r["depth_score"]:.0f}</b></span>'
            f"</div>"
        )

        results_html += f"""
        <div class="result-card">
            <div class="result-header">
                <div class="score-badge" style="background:{color}">{score:.0f}</div>
                <div class="result-meta">
                    <h3><a href="{r['url']}" target="_blank">{_esc(r['title'])}</a></h3>
                    <div class="url-line">
                        <span class="site-tag">{_esc(site)}</span>
                        <a href="{r['url']}" class="url-link" target="_blank">{_esc(r['url'])}</a>
                        {pub_html}
                    </div>
                </div>
                {low_badge}
            </div>
            <p class="snippet">{_esc(r['content'][:500])}</p>
            {criteria_html}
        </div>
"""

    # Timeline section
    timeline_rows = ""
    for event in timeline:
        ts = event["timestamp"]
        try:
            from datetime import datetime as dt_
            d = dt_.fromisoformat(ts)
            ts_display = d.strftime("%H:%M:%S")
        except Exception:
            ts_display = ts[:19]

        site_cell = _esc(event.get("site") or "—")
        details = _esc(event.get("details") or "")
        timeline_rows += f"""
            <tr>
                <td class="ts">{ts_display}</td>
                <td class="agent">{_esc(event['agent'])}</td>
                <td>{_esc(event['action'])}</td>
                <td>{site_cell}</td>
                <td class="details">{details}</td>
            </tr>"""

    # Footer references grouped by site
    ref_map: dict[str, list[str]] = {}
    for r in results:
        site = r.get("site") or "other"
        ref_map.setdefault(site, []).append(r["url"])

    refs_html = ""
    for site, urls in ref_map.items():
        refs_html += f'<div class="ref-group"><strong>{_esc(site)}</strong><ul>'
        for url in urls:
            refs_html += f'<li><a href="{url}" target="_blank">{_esc(url)}</a></li>'
        refs_html += "</ul></div>"

    total = len(results)
    gen_str = generated_at.strftime("%d/%m/%Y %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pesquisa: {_esc(query)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f6fa; color: #2c3e50; line-height: 1.6; }}
  .header {{ background: linear-gradient(135deg, #2c3e50, #3498db); color: white; padding: 2rem; }}
  .header h1 {{ font-size: 1.4rem; font-weight: 400; opacity: 0.8; }}
  .header h2 {{ font-size: 1.8rem; margin: 0.5rem 0; }}
  .header-meta {{ margin-top: 0.5rem; opacity: 0.7; font-size: 0.9rem; }}
  .container {{ max-width: 960px; margin: 2rem auto; padding: 0 1rem; }}
  .section-title {{ font-size: 1.3rem; font-weight: 700; margin: 2rem 0 1rem; color: #2c3e50; border-left: 4px solid #3498db; padding-left: 0.75rem; }}
  .result-card {{ background: white; border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }}
  .result-header {{ display: flex; align-items: flex-start; gap: 1rem; }}
  .score-badge {{ color: white; font-size: 1.2rem; font-weight: 700; border-radius: 8px; width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
  .result-meta {{ flex: 1; }}
  .result-meta h3 {{ font-size: 1rem; margin-bottom: 0.25rem; }}
  .result-meta a {{ color: #2980b9; text-decoration: none; }}
  .result-meta a:hover {{ text-decoration: underline; }}
  .url-line {{ display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-size: 0.82rem; color: #7f8c8d; }}
  .site-tag {{ background: #ecf0f1; border-radius: 4px; padding: 1px 6px; font-size: 0.75rem; color: #555; }}
  .url-link {{ color: #27ae60; word-break: break-all; }}
  .pub-date {{ font-size: 0.75rem; color: #95a5a6; }}
  .badge-low {{ background: #e74c3c; color: white; font-size: 0.7rem; border-radius: 20px; padding: 2px 10px; margin-left: auto; white-space: nowrap; }}
  .snippet {{ margin: 0.75rem 0 0.5rem; font-size: 0.9rem; color: #555; }}
  .criteria {{ display: flex; gap: 1rem; flex-wrap: wrap; font-size: 0.8rem; color: #7f8c8d; margin-top: 0.5rem; }}
  .criteria span {{ background: #f8f9fa; border-radius: 4px; padding: 2px 8px; }}
  /* Timeline */
  .timeline-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }}
  .timeline-table th {{ background: #2c3e50; color: white; padding: 0.6rem 0.8rem; text-align: left; }}
  .timeline-table td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #ecf0f1; vertical-align: top; }}
  .timeline-table tr:last-child td {{ border-bottom: none; }}
  .timeline-table tr:hover td {{ background: #f8f9fa; }}
  .ts {{ font-family: monospace; color: #3498db; white-space: nowrap; }}
  .agent {{ font-weight: 600; color: #8e44ad; white-space: nowrap; }}
  .details {{ color: #7f8c8d; word-break: break-all; max-width: 200px; }}
  /* References */
  .refs {{ background: white; border-radius: 10px; padding: 1.25rem; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }}
  .ref-group {{ margin-bottom: 1rem; }}
  .ref-group ul {{ margin-top: 0.4rem; padding-left: 1.2rem; }}
  .ref-group li {{ margin: 0.2rem 0; font-size: 0.85rem; }}
  .ref-group a {{ color: #2980b9; word-break: break-all; }}
  footer {{ text-align: center; padding: 2rem; color: #95a5a6; font-size: 0.8rem; }}
</style>
</head>
<body>
<div class="header">
  <h1>Relatório de Pesquisa</h1>
  <h2>{_esc(query)}</h2>
  <div class="header-meta">Gerado em {gen_str} &bull; {total} resultado(s) encontrado(s)</div>
</div>
<div class="container">
  <div class="section-title">Resultados Ranqueados</div>
  {results_html if results_html else '<p style="color:#7f8c8d">Nenhum resultado encontrado.</p>'}

  <div class="section-title">Timeline do Processo</div>
  <table class="timeline-table">
    <thead><tr><th>Hora</th><th>Agente</th><th>Ação</th><th>Site</th><th>Detalhes</th></tr></thead>
    <tbody>{timeline_rows}</tbody>
  </table>

  <div class="section-title">Referências por Site</div>
  <div class="refs">{refs_html if refs_html else '<p style="color:#7f8c8d">Sem referências.</p>'}</div>
</div>
<footer>Gerado pelo LangGraph Search Workflow &bull; {gen_str}</footer>
</body>
</html>"""


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
