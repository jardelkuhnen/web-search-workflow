from langgraph.graph import StateGraph, END

from workflow.state import WorkflowState
from workflow.agents.search_agent import search_agent
from workflow.agents.validation_agent import validation_agent
from workflow.agents.timeline_agent import timeline_agent
from workflow.agents.report_agent import report_agent
from workflow.agents.persist_agent import persist_agent


def build_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)

    graph.add_node("search", search_agent)
    graph.add_node("validation", validation_agent)
    graph.add_node("timeline", timeline_agent)
    graph.add_node("report", report_agent)
    graph.add_node("persist", persist_agent)

    graph.set_entry_point("search")
    graph.add_edge("search", "validation")
    graph.add_edge("validation", "persist")
    graph.add_edge("persist", "timeline")
    graph.add_edge("timeline", "report")
    graph.add_edge("report", END)

    return graph.compile()
