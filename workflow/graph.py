import os
from langgraph.graph import StateGraph, END

from workflow.state import WorkflowState
from workflow.agents.retriever_agent import retriever_agent
from workflow.agents.search_agent import search_agent
from workflow.agents.validation_agent import validation_agent
from workflow.agents.timeline_agent import timeline_agent
from workflow.agents.report_agent import report_agent
from workflow.agents.persist_agent import persist_agent


def _route_after_validation(state: WorkflowState) -> str:
    """
    - Se já veio da web (web_searched=True): vai para persist.
    - Se ChromaDB retornou 0 resultados: vai direto para web.
    - Se melhor score >= threshold: cache hit → pula web e persist.
    - Senão: cache miss → busca na web.
    """
    if state.get("web_searched", False):
        return "persist"

    ranked = state.get("ranked_results", [])
    if not ranked:
        return "search"

    try:
        threshold = float(os.environ.get("RETRIEVAL_SCORE_THRESHOLD", "7"))
    except (ValueError, TypeError):
        threshold = 7.0

    best_score_normalized = ranked[0]["score"] / 10  # 0-100 → 0-10
    return "timeline" if best_score_normalized >= threshold else "search"


def build_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)

    graph.add_node("retriever", retriever_agent)
    graph.add_node("search", search_agent)
    graph.add_node("validation", validation_agent)
    graph.add_node("timeline", timeline_agent)
    graph.add_node("report", report_agent)
    graph.add_node("persist", persist_agent)

    graph.set_entry_point("retriever")
    graph.add_edge("retriever", "validation")
    graph.add_conditional_edges(
        "validation",
        _route_after_validation,
        {
            "timeline": "timeline",   # cache hit
            "search": "search",       # cache miss (primeira vez)
            "persist": "persist",     # após busca web (web_searched=True)
        },
    )
    graph.add_edge("search", "validation")
    graph.add_edge("persist", "timeline")
    graph.add_edge("timeline", "report")
    graph.add_edge("report", END)

    return graph.compile()
