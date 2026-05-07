from datetime import datetime, timezone
from uuid import uuid4

import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from workflow.state import RankedResult


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
