from datetime import datetime, timezone
from uuid import uuid4

import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from workflow.state import RankedResult, RawResult


class VectorStore:
    COLLECTION_NAME = "search_results"

    def __init__(self, db_path: str = "./db/") -> None:
        self._client = chromadb.PersistentClient(path=db_path)
        self._collection = self._client.get_or_create_collection(self.COLLECTION_NAME)

    def add_results(
        self,
        query: str,
        results: list[RankedResult],
        embeddings: GoogleGenerativeAIEmbeddings,
    ) -> int:
        """Embeda e persiste os resultados. Retorna número de documentos salvos."""
        if not results:
            return 0

        timestamp = datetime.now(timezone.utc).isoformat()
        texts = [f"{query}\n{r['content']}" for r in results]
        vectors = [embeddings.embed_query(text) for text in texts]

        ids = [str(uuid4()) for _ in results]
        metadatas = [
            {
                "url": r["url"],
                "title": r["title"],
                "site": r["site"] or "",
                "score": r["score"],
                "query": query,
                "timestamp": timestamp,
            }
            for r in results
        ]

        self._collection.add(
            ids=ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas,
        )

        return len(results)

    def query_results(
        self,
        query: str,
        embeddings: GoogleGenerativeAIEmbeddings,
        n_results: int = 5,
        sites: list[str] | None = None,
    ) -> list[RawResult]:
        """Busca semântica no ChromaDB com filtro opcional de sites."""
        vector = embeddings.embed_query(query)

        where: dict | None = None
        if sites:
            if len(sites) == 1:
                where = {"site": {"$eq": sites[0]}}
            else:
                where = {"$or": [{"site": {"$eq": s}} for s in sites]}

        try:
            results = self._collection.query(
                query_embeddings=[vector],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas"],
            )
        except Exception:
            return []

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        raw: list[RawResult] = []
        for doc, meta in zip(docs, metas):
            stored_query = meta.get("query", "")
            prefix = f"{stored_query}\n"
            content = doc[len(prefix):] if doc.startswith(prefix) else doc
            raw.append(
                RawResult(
                    title=meta.get("title", ""),
                    url=meta.get("url", ""),
                    content=content,
                    site=meta.get("site") or None,
                    published_date=None,
                )
            )

        return raw
