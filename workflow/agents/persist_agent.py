from datetime import datetime, timezone

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from core.vector_store import VectorStore
from workflow.state import WorkflowState, TimelineEvent


def persist_agent(state: WorkflowState) -> dict:
    print("[5/5] Persist Agent       → Salvando no ChromaDB...")

    timeline_events: list[TimelineEvent] = []
    ranked_results = state.get("ranked_results", [])
    query = state["query"]
    errors: list[str] = []

    try:
        if not ranked_results:
            timeline_events.append(
                TimelineEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    agent="Persist Agent",
                    action="Embeddings gerados e persistidos no ChromaDB",
                    site=None,
                    query=query,
                    details="0 documentos salvos em ./db/",
                )
            )
            return {"persisted_count": 0, "timeline": timeline_events, "errors": errors}

        embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")
        store = VectorStore(db_path="./db/")
        count = store.add_results(query, ranked_results, embeddings)

        timeline_events.append(
            TimelineEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent="Persist Agent",
                action="Embeddings gerados e persistidos no ChromaDB",
                site=None,
                query=query,
                details=f"{count} documentos salvos em ./db/",
            )
        )
        return {"persisted_count": count, "timeline": timeline_events, "errors": errors}

    except Exception as exc:
        errors.append(f"Persist Agent: {exc}")
        timeline_events.append(
            TimelineEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent="Persist Agent",
                action="Embeddings gerados e persistidos no ChromaDB",
                site=None,
                query=query,
                details=f"Erro na persistência: {exc}",
            )
        )
        return {"persisted_count": 0, "timeline": timeline_events, "errors": errors}
