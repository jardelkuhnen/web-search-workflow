import os
from datetime import datetime, timezone
from tavily import TavilyClient

from workflow.state import WorkflowState, RawResult, TimelineEvent


def search_agent(state: WorkflowState) -> dict:
    print("[1/4] Search Agent        → Buscando resultados...")

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {
            "errors": ["TAVILY_API_KEY não configurada. Verifique o arquivo .env."],
            "raw_results": [],
            "timeline": [_event("Search Agent", "Erro: TAVILY_API_KEY ausente", query=state["query"])],
        }

    client = TavilyClient(api_key=api_key)
    query = state["query"]
    sites = state.get("sites", [])
    timeline_events: list[TimelineEvent] = []
    raw_results: list[RawResult] = []

    # Record workflow start event (if first agent)
    if not state.get("workflow_start"):
        timeline_events.append(_event("Search Agent", "Início do workflow", query=query))

    if sites:
        # Per-site searches
        for site in sites:
            print(f"  - {site}: ", end="", flush=True)
            try:
                response = client.search(
                    query=query,
                    include_domains=[site],
                    max_results=5,
                    search_depth="advanced",
                )
                results = response.get("results", [])
                count = len(results)
                print(f"{count} resultado(s)")

                timeline_events.append(
                    _event(
                        "Search Agent",
                        f"Busca Tavily em {site}",
                        site=site,
                        query=query,
                        details=f"{count} resultado(s)",
                    )
                )

                for r in results:
                    raw_results.append(_to_raw_result(r, site))

                if count == 0:
                    timeline_events.append(
                        _event("Search Agent", f"Sem resultados em {site}", site=site, query=query)
                    )

            except Exception as e:
                msg = f"Timeout/erro ao buscar em {site}: {e}"
                print(f"erro — {e}")
                timeline_events.append(_event("Search Agent", msg, site=site, query=query))
    else:
        # General internet search
        print(f'  Buscando na internet: "{query}"... ', end="", flush=True)
        try:
            response = client.search(
                query=query,
                max_results=5,
                search_depth="advanced",
            )
            results = response.get("results", [])
            count = len(results)
            print(f"{count} resultado(s)")

            timeline_events.append(
                _event(
                    "Search Agent",
                    "Busca Tavily geral (internet aberta)",
                    query=query,
                    details=f"{count} resultado(s)",
                )
            )

            for r in results:
                raw_results.append(_to_raw_result(r, None))

        except Exception as e:
            msg = f"Timeout/erro na busca geral: {e}"
            print(f"erro — {e}")
            timeline_events.append(_event("Search Agent", msg, query=query))

    return {
        "raw_results": raw_results,
        "timeline": timeline_events,
        "workflow_start": state.get("workflow_start") or datetime.now(timezone.utc).isoformat(),
    }


def _event(
    agent: str,
    action: str,
    site: str | None = None,
    query: str | None = None,
    details: str | None = None,
) -> TimelineEvent:
    return TimelineEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent=agent,
        action=action,
        site=site,
        query=query,
        details=details,
    )


def _to_raw_result(r: dict, site: str | None) -> RawResult:
    return RawResult(
        title=r.get("title", ""),
        url=r.get("url", ""),
        content=r.get("content", ""),
        site=site or _extract_domain(r.get("url", "")),
        published_date=r.get("published_date"),
    )


def _extract_domain(url: str) -> str | None:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc or None
    except Exception:
        return None
