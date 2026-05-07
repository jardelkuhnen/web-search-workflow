import os
from datetime import datetime, timezone

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from core.vector_store import VectorStore
from workflow.state import WorkflowState, TimelineEvent


def retriever_agent(state: WorkflowState) -> dict:
    query = state["query"]
    sites = state.get("sites", [])
    print("[1/N] Retriever Agent     → Consultando ChromaDB...")

    timeline_events: list[TimelineEvent] = []
    timeline_events.append(_event("Retriever Agent", "Início do workflow — consultando ChromaDB", query=query))

    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")
        store = VectorStore(db_path="./db/")
        raw_results = store.query_results(
            query=query,
            embeddings=embeddings,
            n_results=5,
            sites=sites if sites else None,
        )
    except Exception as exc:
        timeline_events.append(
            _event("Retriever Agent", f"Erro ao consultar ChromaDB: {exc}", query=query)
        )
        return {
            "raw_results": [],
            "web_searched": False,
            "cache_hit": None,
            "timeline": timeline_events,
            "workflow_start": datetime.now(timezone.utc).isoformat(),
        }

    count = len(raw_results)
    filter_info = f" (filtro: {', '.join(sites)})" if sites else ""
    timeline_events.append(
        _event(
            "Retriever Agent",
            f"Consulta ao ChromaDB concluída{filter_info}",
            query=query,
            details=f"{count} resultado(s) encontrado(s)",
        )
    )

    return {
        "raw_results": raw_results,
        "web_searched": False,
        "cache_hit": None,
        "timeline": timeline_events,
        "workflow_start": datetime.now(timezone.utc).isoformat(),
    }


def _event(agent: str, action: str, site: str | None = None,
           query: str | None = None, details: str | None = None) -> TimelineEvent:
    return TimelineEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent=agent, action=action, site=site, query=query, details=details,
    )
