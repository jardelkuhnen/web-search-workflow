from datetime import datetime, timezone

from workflow.state import WorkflowState, TimelineEvent


def timeline_agent(state: WorkflowState) -> dict:
    timeline = state.get("timeline", [])
    count = len(timeline)
    print(f"[3/4] Timeline Agent      → Compilando timeline ({count} eventos)...")

    # Add the timeline compilation event itself
    new_event = TimelineEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="Timeline Agent",
        action=f"Timeline compilada com {count} eventos",
        site=None,
        query=state.get("query"),
        details=None,
    )

    return {"timeline": [new_event]}


def format_timeline_for_terminal(timeline: list[TimelineEvent]) -> str:
    lines = []
    for event in timeline:
        ts = event["timestamp"]
        try:
            dt = datetime.fromisoformat(ts)
            ts_display = dt.strftime("%H:%M:%S")
        except Exception:
            ts_display = ts[:19]

        agent = event["agent"].ljust(18)
        action = event["action"]
        site = f" | site: {event['site']}" if event.get("site") else ""
        query = f" | query: \"{event['query'][:50]}\"" if event.get("query") else ""
        details = f" | {event['details']}" if event.get("details") else ""

        lines.append(f"  {ts_display} | {agent} | {action}{site}{query}{details}")

    return "\n".join(lines)
