# Vector Persistence with ChromaDB — Technical Spec

**Status**: approved
**Feature**: 002
**Owner**: jardel.kuhnen@mercadolivre.com
**Created**: 2026-05-06

---

## Architecture Overview

```
workflow/graph.py — LangGraph graph (atualizado)

  search_agent → validation_agent → timeline_agent → report_agent → persist_agent → END

Novo nó: persist_agent
  ┌─────────────────────────────────────────────────────┐
  │  persist_agent                                      │
  │                                                     │
  │  1. Inicializa ChromaDB PersistentClient → ./db/    │
  │  2. Obtém ou cria coleção search_results            │
  │  3. Para cada ranked_result:                        │
  │     - texto = f"{query}\n{result['content']}"       │
  │     - metadados = {url, title, site, score,         │
  │                    query, timestamp}                │
  │     - id = str(uuid4())                             │
  │  4. Chama GoogleGenerativeAIEmbeddings em batch     │
  │  5. Adiciona documentos à coleção                   │
  │  6. Registra TimelineEvent                          │
  │  7. Atualiza state["persisted_count"]               │
  └─────────────────────────────────────────────────────┘
```

---

## New Files

| Arquivo | Descrição |
|---------|-----------|
| `workflow/agents/persist_agent.py` | Novo agente LangGraph |
| `core/vector_store.py` | Abstração do ChromaDB (client + coleção) |

## Modified Files

| Arquivo | Mudança |
|---------|---------|
| `workflow/graph.py` | Adicionar nó `persist` e edge `report → persist` |
| `workflow/state.py` | Adicionar campo `persisted_count: int` |
| `requirements.txt` | Adicionar `chromadb` |
| `.gitignore` | Adicionar entrada `db/` |

---

## Data Model

### Documento ChromaDB

Cada `RankedResult` gera um documento com a seguinte estrutura:

```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",  # uuid4
    "document": "cadeiras ergonômicas\nAs melhores cadeiras para quem tem 1,93m...",
    "metadata": {
        "url": "https://exemplo.com/artigo",
        "title": "Top 10 Cadeiras Ergonômicas",
        "site": "exemplo.com",
        "score": 87.5,
        "query": "cadeiras ergonômicas",
        "timestamp": "2026-05-06T14:30:29Z"
    }
}
```

### Coleção ChromaDB

| Propriedade | Valor |
|-------------|-------|
| Nome | `search_results` |
| Diretório | `./db/` |
| Client | `chromadb.PersistentClient(path="./db/")` |
| Criação | `get_or_create_collection("search_results")` |

---

## API Contracts (Internal)

### `core/vector_store.py`

```python
class VectorStore:
    def __init__(self, db_path: str = "./db/") -> None: ...

    def add_results(
        self,
        query: str,
        results: list[RankedResult],
        embeddings: GoogleGenerativeAIEmbeddings,
    ) -> int:
        """Embeda e persiste os resultados. Retorna número de documentos salvos."""
        ...
```

### `workflow/agents/persist_agent.py`

```python
def persist_agent(state: WorkflowState) -> dict:
    """
    LangGraph node: embeda e persiste ranked_results no ChromaDB.
    Retorna: {"persisted_count": N, "timeline": [...], "errors": [...]}
    Erro é não-fatal — workflow não é interrompido.
    """
```

---

## WorkflowState — Novo Campo

```python
# workflow/state.py
class WorkflowState(TypedDict):
    # ... campos existentes ...
    persisted_count: int  # novo — número de documentos persistidos no ChromaDB
```

---

## LangGraph Graph — Atualização

```python
# workflow/graph.py
from workflow.agents.persist_agent import persist_agent

def build_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)

    graph.add_node("search", search_agent)
    graph.add_node("validation", validation_agent)
    graph.add_node("timeline", timeline_agent)
    graph.add_node("report", report_agent)
    graph.add_node("persist", persist_agent)   # novo

    graph.set_entry_point("search")
    graph.add_edge("search", "validation")
    graph.add_edge("validation", "timeline")
    graph.add_edge("timeline", "report")
    graph.add_edge("report", "persist")         # novo
    graph.add_edge("persist", END)              # atualizado

    return graph.compile()
```

---

## Embedding Strategy

| Propriedade | Valor |
|-------------|-------|
| Classe | `GoogleGenerativeAIEmbeddings` |
| Modelo | `models/embedding-001` |
| API Key | `GOOGLE_API_KEY` (já presente no `.env`) |
| Estratégia | Batch: `embed_documents([text1, text2, ...])` |
| Texto embeddado | `f"{query}\n{result['content']}"` |

```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
vectors = embeddings.embed_documents(texts)  # list de strings
```

---

## Error Handling

| Cenário | Comportamento |
|---------|---------------|
| `ranked_results` vazio | Retorna `persisted_count=0`, registra na timeline, sem erro |
| Google API falha (timeout/quota) | Captura exceção, adiciona a `state["errors"]`, timeline com detalhe, `persisted_count=0` |
| ChromaDB I/O error (disco cheio) | Captura exceção, adiciona a `state["errors"]`, timeline com detalhe |
| Qualquer exceção não prevista | `try/except Exception`, nunca propaga para o grafo |

---

## Dependencies

```
chromadb>=0.6.0
langchain-google-genai>=4.2.2  # já presente
```

Adicionar ao `requirements.txt`:
```
chromadb>=0.6.0
```

---

## .gitignore

Adicionar:
```
db/
```

---

## Design Decisions

| Decisão | Escolha | Rationale |
|---------|---------|-----------|
| Client ChromaDB | `PersistentClient` | Persiste em disco; sem servidor externo necessário |
| Coleção | Única (`search_results`) | Simplifica queries futuras (feat-003); toda informação em um lugar |
| IDs dos documentos | `uuid4()` | Garante unicidade sem depender de hash de conteúdo |
| Embedding em batch | `embed_documents(texts)` | Uma chamada de API para todos os resultados da execução |
| Erro não-fatal | `try/except` no agente | Persistência é auxiliar; o relatório HTML já foi gerado |
| Abstração `VectorStore` | `core/vector_store.py` | Isola a lógica ChromaDB para facilitar troca futura e testes |

---

## Testing Strategy

| Teste | Tipo | Foco |
|-------|------|------|
| `test_persist_agent_success` | Unit | Verifica `persisted_count == len(ranked_results)` e evento na timeline |
| `test_persist_agent_empty_results` | Unit | `ranked_results=[]` → `persisted_count=0`, sem erro |
| `test_persist_agent_api_error` | Unit | Mock Google API raise → erro não-fatal, `state["errors"]` preenchido |
| `test_vector_store_add_results` | Unit | Verifica estrutura de documentos gerados (ids, metadados) |
