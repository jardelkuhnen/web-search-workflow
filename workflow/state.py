from typing import TypedDict, Annotated
import operator


class TimelineEvent(TypedDict):
    timestamp: str
    agent: str
    action: str
    site: str | None
    query: str | None
    details: str | None


class RawResult(TypedDict):
    title: str
    url: str
    content: str
    site: str | None
    published_date: str | None


class RankedResult(TypedDict):
    title: str
    url: str
    content: str
    site: str | None
    published_date: str | None
    score: float
    relevance_score: float
    credibility_score: float
    recency_score: float
    depth_score: float


class WorkflowState(TypedDict):
    # Input
    query: str
    sites: list[str]
    sites_group: str | None

    # Agent outputs
    raw_results: list[RawResult]
    ranked_results: list[RankedResult]
    timeline: Annotated[list[TimelineEvent], operator.add]
    html_path: str | None

    # Cache control
    web_searched: bool
    cache_hit: bool | None

    # Runtime
    errors: Annotated[list[str], operator.add]
    workflow_start: str | None
    persisted_count: int
