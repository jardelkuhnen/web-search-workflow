# Vector Persistence with ChromaDB — Functional Spec

**Status**: approved
**Feature**: 002
**Owner**: jardel.kuhnen@mercadolivre.com
**Created**: 2026-05-06

---

## Problem Statement

Atualmente, cada execução do workflow realiza chamadas à API Tavily e ao LLM do zero, sem nenhum registro persistente dos resultados. Pesquisas repetidas ou semanticamente similares consomem API calls desnecessários e perdem o histórico de resultados anteriores.

Esta entrega implementa a **camada de persistência**: ao final de cada pesquisa, os resultados ranqueados são embeddados e gravados no ChromaDB local. Isso prepara o terreno para a próxima entrega, que consultará esse banco antes de chamar a web.

---

## Objectives

1. Ao final de cada execução do workflow, persistir automaticamente os resultados no ChromaDB
2. Embedar a query do usuário e o conteúdo de cada resultado usando Google Embeddings
3. Armazenar metadados completos de cada resultado junto ao vetor
4. Manter o banco de dados em `./db/` (persistência local, sem dependências externas)
5. Registrar o evento de persistência na timeline do workflow

---

## Scope

### In Scope
- Novo agente `persist_agent` adicionado ao final do grafo LangGraph (após `report`)
- Embedding da query do usuário + content (snippet) de cada `RankedResult`
- Persistência no ChromaDB em coleção `search_results` no diretório `./db/`
- Metadados armazenados por documento: `url`, `title`, `site`, `score`, `query`, `timestamp`
- Registro na timeline: evento de persistência com número de documentos salvos
- Novo campo no `WorkflowState`: `persisted_count: int`
- Criação automática do diretório `./db/` se não existir
- Modelo de embedding: `GoogleGenerativeAIEmbeddings` com `models/embedding-001`

### Out of Scope
- Consulta ao ChromaDB antes de chamar a web (próxima entrega — feat-003)
- Deduplicação semântica (feat-003)
- Interface CLI para buscar no histórico
- Exportação do banco de dados
- Remoção ou atualização de registros existentes

---

## User Stories

### US-1: Persistência automática ao final da pesquisa

**As a** pesquisador,
**I want** que os resultados de cada pesquisa sejam automaticamente salvos no ChromaDB,
**So that** eu construa um histórico local reutilizável sem nenhuma ação extra.

**Acceptance Criteria**:
- Após a geração do relatório HTML, o `persist_agent` é executado automaticamente
- Cada `RankedResult` é convertido em um documento com: texto = `f"{query}\n{result.content}"` e metadados = `{url, title, site, score, query, timestamp}`
- Todos os documentos da execução são adicionados à coleção `search_results` em `./db/`
- O campo `persisted_count` no estado final reflete o número de documentos gravados
- Se não houver `ranked_results`, o agente encerra sem erro (0 documentos persistidos)

**Priority**: High

---

### US-2: Evento de persistência na timeline

**As a** pesquisador,
**I want** ver na timeline quantos resultados foram salvos no ChromaDB,
**So that** eu tenha rastreabilidade completa do processo incluindo a etapa de persistência.

**Acceptance Criteria**:
- O `persist_agent` registra um `TimelineEvent` com: `agent="Persist Agent"`, `action="Embeddings gerados e persistidos no ChromaDB"`, `details=f"{N} documentos salvos em ./db/"`
- O evento aparece no terminal ao final da execução e no relatório HTML
- Em caso de erro na persistência: o evento registra o erro em `details`, o workflow **não** é interrompido (erro não-fatal), e o erro é adicionado a `state["errors"]`

**Priority**: High

---

### US-3: Diretório `db/` gerenciado automaticamente

**As a** desenvolvedor,
**I want** que o diretório `./db/` seja criado automaticamente se não existir,
**So that** não precise configurar nada manualmente antes da primeira execução.

**Acceptance Criteria**:
- Na primeira execução, `./db/` é criado pelo ChromaDB PersistentClient sem intervenção do usuário
- O `.gitignore` deve conter entrada para `db/` (não versionar o banco local)
- A coleção `search_results` é criada automaticamente se não existir; se já existir, os novos documentos são **adicionados** (sem apagar dados anteriores)

**Priority**: Medium

---

## User Experience

### Fluxo atualizado no terminal

```
$ python main.py --query="cadeiras ergonômicas"

[1/4] Search Agent        → Buscando "cadeiras ergonômicas"...
[2/4] Validation Agent    → Ranqueando 5 resultados...
[3/4] Timeline Agent      → Compilando timeline...
[4/4] Report Agent        → Gerando HTML...
[5/5] Persist Agent       → Salvando no ChromaDB...

✅ Concluído em 26s
📄 Relatório: ./search_20260506_143022.html (aberto no browser)

Timeline:
  ...
  14:30:29 | Persist Agent | Embeddings gerados e persistidos no ChromaDB | 5 documentos salvos em ./db/
```

---

## Success Metrics

1. 100% dos `ranked_results` de cada execução são persistidos no ChromaDB (0 perdas)
2. Tempo adicional do `persist_agent` < 10 segundos para até 25 resultados
3. A coleção `search_results` acumula documentos entre execuções (sem apagar dados anteriores)
4. Erro na persistência não interrompe o workflow (erro não-fatal registrado em `state["errors"]`)

---

## Business Rules

- **Texto embeddado**: concatenação de query + content do resultado: `f"{query}\n{result['content']}"`
- **Coleção única**: todos os resultados de todas as execuções vão para a coleção `search_results`
- **IDs únicos**: gerado via `uuid4()` por documento para evitar colisões
- **Erro não-fatal**: falha na persistência (ex: Google API key inválida) é logada na timeline e em `state["errors"]`, mas não encerra o workflow
- **Diretório**: sempre `./db/` relativo ao diretório de execução

---

## Dependencies

- `chromadb` — banco vetorial local
- `langchain-google-genai` — já presente no projeto (`GoogleGenerativeAIEmbeddings`)
- `GOOGLE_API_KEY` — já exigida pelo workflow existente
- Grafo LangGraph existente em `workflow/graph.py` — novo nó `persist` adicionado após `report`

---

## Risks

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Google Embeddings API lenta | Média | Médio | Erro não-fatal; timeout de 30s; registrar na timeline |
| Disco cheio | Baixa | Alto | Erro capturado e logado; workflow continua |
| Incompatibilidade de versão ChromaDB | Baixa | Alto | Fixar versão no requirements.txt |
