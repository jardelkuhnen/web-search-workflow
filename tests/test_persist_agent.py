"""
Tests for persist_agent and VectorStore.

Note: langchain_google_genai depends on google-genai which causes SIGILL on this
ARM64 environment due to the _interactions package. We stub the module in sys.modules
before importing our code so tests can run without the broken SDK.
"""
import sys
from unittest.mock import MagicMock

# Stub out google-genai and langchain-google-genai before any project imports.
# google-genai >= 1.5 ships a `_interactions` sub-package that causes SIGILL on
# this ARM64 devcontainer environment. We stub only the affected namespaces while
# leaving google.protobuf (needed by chromadb's OpenTelemetry stack) untouched.
_mock_lgn = MagicMock()
sys.modules.setdefault("langchain_google_genai", _mock_lgn)
sys.modules.setdefault("langchain_google_genai.embeddings", _mock_lgn)
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())
sys.modules.setdefault("google.genai._interactions", MagicMock())
sys.modules.setdefault("google.auth", MagicMock())

from unittest.mock import patch  # noqa: E402

from workflow.agents.persist_agent import persist_agent  # noqa: E402
from workflow.state import RankedResult, WorkflowState  # noqa: E402


def _make_ranked_result(i: int) -> RankedResult:
    return RankedResult(
        title=f"Title {i}",
        url=f"https://example.com/{i}",
        content=f"Content {i}",
        site="example.com",
        published_date=None,
        score=80.0,
        relevance_score=80.0,
        credibility_score=80.0,
        recency_score=80.0,
        depth_score=80.0,
    )


def _base_state(ranked_results=None) -> WorkflowState:
    return WorkflowState(
        query="test query",
        sites=[],
        sites_group=None,
        raw_results=[],
        ranked_results=ranked_results or [],
        timeline=[],
        html_path=None,
        errors=[],
        workflow_start=None,
        persisted_count=0,
    )


class TestPersistAgentSuccess:
    @patch("workflow.agents.persist_agent.VectorStore")
    @patch("workflow.agents.persist_agent.GoogleGenerativeAIEmbeddings")
    def test_persisted_count_equals_results(self, mock_emb_cls, mock_vs_cls):
        results = [_make_ranked_result(i) for i in range(3)]
        mock_store = MagicMock()
        mock_store.add_results.return_value = 3
        mock_vs_cls.return_value = mock_store

        state = _base_state(ranked_results=results)
        output = persist_agent(state)

        assert output["persisted_count"] == 3
        assert output["errors"] == []
        assert len(output["timeline"]) == 1
        assert "3 documentos" in output["timeline"][0]["details"]

    @patch("workflow.agents.persist_agent.VectorStore")
    @patch("workflow.agents.persist_agent.GoogleGenerativeAIEmbeddings")
    def test_timeline_event_agent_name(self, mock_emb_cls, mock_vs_cls):
        mock_store = MagicMock()
        mock_store.add_results.return_value = 1
        mock_vs_cls.return_value = mock_store

        state = _base_state(ranked_results=[_make_ranked_result(0)])
        output = persist_agent(state)

        assert output["timeline"][0]["agent"] == "Persist Agent"
        assert output["timeline"][0]["action"] == "Embeddings gerados e persistidos no ChromaDB"


class TestPersistAgentEmptyResults:
    def test_empty_results_returns_zero(self):
        state = _base_state(ranked_results=[])
        output = persist_agent(state)

        assert output["persisted_count"] == 0

    def test_empty_results_no_error(self):
        state = _base_state(ranked_results=[])
        output = persist_agent(state)

        assert output["errors"] == []

    def test_empty_results_records_timeline(self):
        state = _base_state(ranked_results=[])
        output = persist_agent(state)

        assert len(output["timeline"]) == 1
        assert "0 documentos" in output["timeline"][0]["details"]


class TestPersistAgentApiError:
    @patch("workflow.agents.persist_agent.VectorStore")
    @patch("workflow.agents.persist_agent.GoogleGenerativeAIEmbeddings")
    def test_api_error_non_fatal(self, mock_emb_cls, mock_vs_cls):
        mock_vs_cls.side_effect = Exception("API quota exceeded")
        state = _base_state(ranked_results=[_make_ranked_result(0)])

        output = persist_agent(state)

        assert output["persisted_count"] == 0
        assert len(output["errors"]) == 1
        assert "API quota exceeded" in output["errors"][0]

    @patch("workflow.agents.persist_agent.VectorStore")
    @patch("workflow.agents.persist_agent.GoogleGenerativeAIEmbeddings")
    def test_api_error_timeline_detail(self, mock_emb_cls, mock_vs_cls):
        mock_vs_cls.side_effect = Exception("API quota exceeded")
        state = _base_state(ranked_results=[_make_ranked_result(0)])

        output = persist_agent(state)

        assert "Erro na persistência" in output["timeline"][0]["details"]

    @patch("workflow.agents.persist_agent.VectorStore")
    @patch("workflow.agents.persist_agent.GoogleGenerativeAIEmbeddings")
    def test_workflow_continues_after_error(self, mock_emb_cls, mock_vs_cls):
        mock_vs_cls.side_effect = RuntimeError("disk full")
        state = _base_state(ranked_results=[_make_ranked_result(0)])

        # Should not raise
        output = persist_agent(state)
        assert output is not None


class TestVectorStoreAddResults:
    @patch("core.vector_store.chromadb.PersistentClient")
    def test_document_count(self, mock_client_cls):
        from core.vector_store import VectorStore

        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]

        results = [_make_ranked_result(0), _make_ranked_result(1)]
        store = VectorStore(db_path="./db/")
        count = store.add_results("test query", results, mock_embeddings)

        assert count == 2

    @patch("core.vector_store.chromadb.PersistentClient")
    def test_document_metadata_structure(self, mock_client_cls):
        from core.vector_store import VectorStore

        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1, 0.2]]

        results = [_make_ranked_result(0)]
        store = VectorStore(db_path="./db/")
        store.add_results("test query", results, mock_embeddings)

        call_kwargs = mock_collection.add.call_args.kwargs
        meta = call_kwargs["metadatas"][0]
        assert meta["url"] == "https://example.com/0"
        assert meta["query"] == "test query"
        assert meta["title"] == "Title 0"
        assert "score" in meta
        assert "timestamp" in meta

    @patch("core.vector_store.chromadb.PersistentClient")
    def test_document_text_format(self, mock_client_cls):
        from core.vector_store import VectorStore

        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1, 0.2]]

        results = [_make_ranked_result(0)]
        store = VectorStore(db_path="./db/")
        store.add_results("test query", results, mock_embeddings)

        call_kwargs = mock_collection.add.call_args.kwargs
        assert call_kwargs["documents"][0] == "test query\nContent 0"

    @patch("core.vector_store.chromadb.PersistentClient")
    def test_unique_ids_per_document(self, mock_client_cls):
        from core.vector_store import VectorStore

        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_client
        mock_client_cls.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1], [0.2], [0.3]]

        results = [_make_ranked_result(i) for i in range(3)]
        store = VectorStore(db_path="./db/")
        store.add_results("test query", results, mock_embeddings)

        call_kwargs = mock_collection.add.call_args.kwargs
        ids = call_kwargs["ids"]
        assert len(ids) == 3
        assert len(set(ids)) == 3  # all unique

    @patch("core.vector_store.chromadb.PersistentClient")
    def test_empty_results_returns_zero(self, mock_client_cls):
        from core.vector_store import VectorStore

        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        mock_embeddings = MagicMock()
        store = VectorStore(db_path="./db/")
        count = store.add_results("test query", [], mock_embeddings)

        assert count == 0
        mock_collection.add.assert_not_called()
