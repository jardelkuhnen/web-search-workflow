"""
Unit tests for _route_after_validation in workflow/graph.py.
"""
import sys
from unittest.mock import MagicMock

_mock_lgn = MagicMock()
sys.modules.setdefault("langchain_google_genai", _mock_lgn)
sys.modules.setdefault("langchain_google_genai.embeddings", _mock_lgn)
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())
sys.modules.setdefault("google.genai._interactions", MagicMock())
sys.modules.setdefault("google.auth", MagicMock())

import os  # noqa: E402
from unittest.mock import patch  # noqa: E402

from workflow.graph import _route_after_validation  # noqa: E402
from workflow.state import RankedResult, WorkflowState  # noqa: E402


def _make_ranked_result(score: float) -> RankedResult:
    return RankedResult(
        title="T",
        url="https://x.com",
        content="c",
        site="x.com",
        published_date=None,
        score=score,
        relevance_score=score,
        credibility_score=score,
        recency_score=score,
        depth_score=score,
    )


def _make_state(ranked_results=None, web_searched=False) -> WorkflowState:
    return WorkflowState(
        query="q",
        sites=[],
        sites_group=None,
        raw_results=[],
        ranked_results=ranked_results or [],
        timeline=[],
        html_path=None,
        web_searched=web_searched,
        cache_hit=None,
        errors=[],
        workflow_start=None,
        persisted_count=0,
    )


class TestRouteCacheHit:
    def test_score_at_threshold_routes_to_timeline(self):
        # score=70 → normalized=7.0 >= 7.0 → timeline
        state = _make_state(ranked_results=[_make_ranked_result(70.0)])
        with patch.dict(os.environ, {"RETRIEVAL_SCORE_THRESHOLD": "7"}):
            assert _route_after_validation(state) == "timeline"

    def test_score_above_threshold_routes_to_timeline(self):
        state = _make_state(ranked_results=[_make_ranked_result(90.0)])
        with patch.dict(os.environ, {"RETRIEVAL_SCORE_THRESHOLD": "7"}):
            assert _route_after_validation(state) == "timeline"


class TestRouteCacheMiss:
    def test_score_below_threshold_routes_to_search(self):
        # score=60 → normalized=6.0 < 7.0 → search
        state = _make_state(ranked_results=[_make_ranked_result(60.0)])
        with patch.dict(os.environ, {"RETRIEVAL_SCORE_THRESHOLD": "7"}):
            assert _route_after_validation(state) == "search"


class TestRouteWebSearched:
    def test_web_searched_true_routes_to_persist(self):
        state = _make_state(
            ranked_results=[_make_ranked_result(90.0)],
            web_searched=True,
        )
        assert _route_after_validation(state) == "persist"

    def test_web_searched_true_ignores_score(self):
        state = _make_state(
            ranked_results=[_make_ranked_result(10.0)],
            web_searched=True,
        )
        assert _route_after_validation(state) == "persist"


class TestRouteEmptyResults:
    def test_empty_ranked_results_routes_to_search(self):
        state = _make_state(ranked_results=[])
        assert _route_after_validation(state) == "search"

    def test_none_ranked_results_routes_to_search(self):
        state = _make_state(ranked_results=None)
        assert _route_after_validation(state) == "search"


class TestThresholdDefault:
    def test_missing_env_var_uses_default_7(self):
        # score=65 → normalized=6.5 < 7.0 → search (default=7)
        state = _make_state(ranked_results=[_make_ranked_result(65.0)])
        env = {k: v for k, v in os.environ.items() if k != "RETRIEVAL_SCORE_THRESHOLD"}
        with patch.dict(os.environ, env, clear=True):
            assert _route_after_validation(state) == "search"

    def test_invalid_env_var_uses_default_7(self):
        state = _make_state(ranked_results=[_make_ranked_result(65.0)])
        with patch.dict(os.environ, {"RETRIEVAL_SCORE_THRESHOLD": "not_a_number"}):
            assert _route_after_validation(state) == "search"
