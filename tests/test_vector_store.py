"""
Unit tests for VectorStore.query_results().
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

from unittest.mock import patch  # noqa: E402

from core.vector_store import VectorStore  # noqa: E402


def _make_collection_response(docs, metas):
    return {"documents": [docs], "metadatas": [metas]}


def _make_mock_store(collection_response):
    with patch("core.vector_store.chromadb.PersistentClient") as mock_client_cls:
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client
        mock_collection.query.return_value = collection_response
        store = VectorStore(db_path="./db/")
        store._collection = mock_collection
        return store, mock_collection


class TestQueryResultsNoFilter:
    @patch("core.vector_store.chromadb.PersistentClient")
    def test_returns_raw_results(self, mock_client_cls):
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        mock_collection.query.return_value = _make_collection_response(
            ["my query\nsome content"],
            [{"title": "Title", "url": "https://x.com", "site": "x.com", "query": "my query"}],
        )

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2]

        store = VectorStore(db_path="./db/")
        results = store.query_results("my query", mock_embeddings)

        assert len(results) == 1
        assert results[0]["title"] == "Title"
        assert results[0]["url"] == "https://x.com"
        assert results[0]["content"] == "some content"
        assert results[0]["site"] == "x.com"

    @patch("core.vector_store.chromadb.PersistentClient")
    def test_no_filter_passes_none_where(self, mock_client_cls):
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client
        mock_collection.query.return_value = _make_collection_response([], [])

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1]

        store = VectorStore(db_path="./db/")
        store.query_results("q", mock_embeddings, sites=None)

        call_kwargs = mock_collection.query.call_args.kwargs
        assert call_kwargs["where"] is None


class TestQueryResultsSiteFilter:
    @patch("core.vector_store.chromadb.PersistentClient")
    def test_single_site_uses_eq_filter(self, mock_client_cls):
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client
        mock_collection.query.return_value = _make_collection_response([], [])

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1]

        store = VectorStore(db_path="./db/")
        store.query_results("q", mock_embeddings, sites=["example.com"])

        call_kwargs = mock_collection.query.call_args.kwargs
        assert call_kwargs["where"] == {"site": {"$eq": "example.com"}}


class TestQueryResultsMultiSiteFilter:
    @patch("core.vector_store.chromadb.PersistentClient")
    def test_multi_site_uses_or_filter(self, mock_client_cls):
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client
        mock_collection.query.return_value = _make_collection_response([], [])

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1]

        store = VectorStore(db_path="./db/")
        store.query_results("q", mock_embeddings, sites=["a.com", "b.com"])

        call_kwargs = mock_collection.query.call_args.kwargs
        assert call_kwargs["where"] == {
            "$or": [{"site": {"$eq": "a.com"}}, {"site": {"$eq": "b.com"}}]
        }


class TestQueryResultsEmptyCollection:
    @patch("core.vector_store.chromadb.PersistentClient")
    def test_returns_empty_list_on_exception(self, mock_client_cls):
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client
        mock_collection.query.side_effect = Exception("collection is empty")

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1]

        store = VectorStore(db_path="./db/")
        results = store.query_results("q", mock_embeddings)

        assert results == []

    @patch("core.vector_store.chromadb.PersistentClient")
    def test_returns_empty_list_when_no_docs(self, mock_client_cls):
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client
        mock_collection.query.return_value = _make_collection_response([], [])

        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1]

        store = VectorStore(db_path="./db/")
        results = store.query_results("q", mock_embeddings)

        assert results == []
