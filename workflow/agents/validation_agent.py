import os
import json
from datetime import datetime, timezone
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from workflow.state import WorkflowState, RankedResult, RawResult, TimelineEvent


SCORING_SYSTEM_PROMPT = """You are an expert research analyst. Your task is to evaluate search results and assign quality scores.

For each result, score these 4 criteria from 0 to 100:
1. **relevance** (0-100): How directly relevant is the content to the query? Does it answer the question?
2. **credibility** (0-100): How trustworthy is the source? Consider: domain authority, known brands, academic/gov sites score higher.
3. **recency** (0-100): How recent is the content? Recent dates score higher. Unknown date = 50 (neutral).
4. **depth** (0-100): How detailed and substantive is the content? Long, informative content scores higher.

Respond with a JSON array. Each element must have:
{
  "index": <int>,
  "relevance": <0-100>,
  "credibility": <0-100>,
  "recency": <0-100>,
  "depth": <0-100>
}

Return ONLY the JSON array, no explanation."""


def validation_agent(state: WorkflowState) -> dict:
    raw_results = state.get("raw_results", [])
    count = len(raw_results)
    print(f"[2/4] Validation Agent    → Ranqueando {count} resultado(s)...")

    timeline_events: list[TimelineEvent] = []
    timeline_events.append(
        _event("Validation Agent", f"Início do ranking de {count} resultado(s)", query=state["query"])
    )

    if not raw_results:
        timeline_events.append(_event("Validation Agent", "Nenhum resultado para rankear"))
        return {"ranked_results": [], "timeline": timeline_events}

    scores = _score_with_llm(raw_results, state["query"])

    ranked: list[RankedResult] = []
    for i, result in enumerate(raw_results):
        s = scores.get(i, {"relevance": 50, "credibility": 50, "recency": 50, "depth": 50})
        total = (s["relevance"] + s["credibility"] + s["recency"] + s["depth"]) / 4
        ranked.append(
            RankedResult(
                title=result["title"],
                url=result["url"],
                content=result["content"],
                site=result.get("site"),
                published_date=result.get("published_date"),
                score=round(total, 1),
                relevance_score=float(s["relevance"]),
                credibility_score=float(s["credibility"]),
                recency_score=float(s["recency"]),
                depth_score=float(s["depth"]),
            )
        )

    ranked.sort(key=lambda r: r["score"], reverse=True)

    timeline_events.append(
        _event(
            "Validation Agent",
            f"Ranking concluído — {len(ranked)} resultado(s) ordenados por score",
            query=state["query"],
            details=f"Scores: {[r['score'] for r in ranked]}",
        )
    )

    return {"ranked_results": ranked, "timeline": timeline_events}


def _score_with_llm(results: list[RawResult], query: str) -> dict[int, dict]:
    model_name = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
    api_key = os.environ.get("GOOGLE_API_KEY")

    results_text = ""
    for i, r in enumerate(results):
        results_text += (
            f"\n--- Result {i} ---\n"
            f"Title: {r['title']}\n"
            f"URL: {r['url']}\n"
            f"Published: {r.get('published_date', 'unknown')}\n"
            f"Content: {r['content'][:800]}\n"
        )

    user_prompt = f"Query: {query}\n\nResults to evaluate:{results_text}"

    try:
        # Uses Google's OpenAI-compatible REST endpoint — no gRPC required
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            temperature=0,
            timeout=60,
        )
        messages = [
            SystemMessage(content=SCORING_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = llm.invoke(messages)
        raw = response.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        items = json.loads(raw)
        return {item["index"]: item for item in items}

    except Exception as e:
        print(f"  [!] LLM timeout/erro: {e}. Usando score neutro (50) para todos os critérios.")
        return {i: {"relevance": 50, "credibility": 50, "recency": 50, "depth": 50} for i in range(len(results))}


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
