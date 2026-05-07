# Functional Specification — ChromaDB Cache Retriever

**Feature**: feat-003
**Status**: Approved
**Date**: 2026-05-07

---

## 1. Problem Statement

O workflow atual realiza busca na web (Tavily) para toda consulta, mesmo quando resultados similares já foram pesquisados anteriormente e estão armazenados no ChromaDB. Isso gera latência desnecessária (5–15s por busca), consumo de quota da API Tavily e custo de chamadas LLM de validação.

## 2. Objectives

- Reutilizar resultados já armazenados no ChromaDB quando a qualidade for suficiente
- Reduzir latência e consumo de API nas consultas recorrentes ou semanticamente similares
- Manter rastreabilidade completa na timeline indicando se o resultado veio do cache ou da web

## 3. Success Metrics

- Consultas com score de cache >= threshold completam sem chamar a API Tavily
- Timeline registra evento de consulta ao banco em todas as execuções
- Score threshold é configurável via `.env` sem mudanças de código

---

## 4. User Stories

### US-001 — Consulta ao cache antes da web

**Como** usuário do workflow,
**quero** que o sistema consulte primeiro o ChromaDB antes de fazer busca na web,
**para** obter respostas mais rápidas quando resultados similares já estiverem armazenados.

**Critérios de Aceitação:**
- AC-001a: O workflow sempre inicia consultando o ChromaDB
- AC-001b: Se os resultados do cache tiverem score >= threshold, a busca na web é ignorada
- AC-001c: Se o ChromaDB estiver vazio ou com score < threshold, o workflow executa busca na web normalmente

---

### US-002 — Filtro de sites na consulta ao cache

**Como** usuário,
**quero** que o filtro de sites (`--sites` ou `--sites-group`) seja aplicado também na busca ao ChromaDB,
**para** que os resultados do cache sejam consistentes com os filtros solicitados.

**Critérios de Aceitação:**
- AC-002a: Quando sites são informados, a consulta ao ChromaDB filtra por `site` nos metadados
- AC-002b: Quando nenhum site é informado, a consulta ao ChromaDB retorna resultados de qualquer site

---

### US-003 — Score threshold configurável

**Como** usuário,
**quero** configurar o score mínimo para aceitar resultados do cache via variável de ambiente,
**para** controlar o trade-off entre velocidade (usar cache) e atualidade (buscar na web).

**Critérios de Aceitação:**
- AC-003a: A variável `RETRIEVAL_SCORE_THRESHOLD` no `.env` define o threshold
- AC-003b: Se a variável não estiver configurada, o valor padrão é `7` (escala 0–10)
- AC-003c: Valores inválidos ou ausentes não travam o workflow (usa default silenciosamente)

---

### US-004 — Rastreabilidade na timeline

**Como** usuário,
**quero** ver na timeline todos os eventos relevantes da consulta ao cache,
**para** entender se o resultado veio do banco ou da web e por quê.

**Critérios de Aceitação:**
- AC-004a: A timeline registra o evento "Consulta ao ChromaDB" com número de resultados encontrados
- AC-004b: A timeline registra o evento "Análise pelo Validation Agent" com os scores obtidos
- AC-004c: Quando score < threshold, a timeline registra o evento "Cache insuficiente — busca na web acionada"
- AC-004d: Quando score >= threshold, a timeline indica "Cache hit — busca na web ignorada"

---

## 5. Scope

### In Scope
- Novo node `retriever_agent` no grafo LangGraph
- Embedding da query via `gemini-embedding-2` (mesmo modelo do persist)
- Consulta semântica ao ChromaDB com filtro opcional de sites
- Roteamento condicional após `validation_agent` baseado em score
- Eventos de timeline para cada etapa (cache query, validation, decisão web)
- Variável `RETRIEVAL_SCORE_THRESHOLD` no `.env`
- Novo método `query_results()` no `VectorStore`

### Out of Scope
- TTL ou expiração automática de registros no ChromaDB
- Interface de gestão do cache
- Alteração no formato de armazenamento existente (persist agent)
- Busca híbrida (cache + web simultâneos)

---

## 6. Business Rules

- **BR-001**: O threshold é comparado em escala 0–10. O score do `validation_agent` (0–100) é normalizado dividindo por 10.
- **BR-002**: O score avaliado é o do melhor resultado após ordenação (`ranked_results[0].score / 10`).
- **BR-003**: Se o ChromaDB retornar 0 resultados, o workflow vai direto para busca na web (não executa validation desnecessariamente).
- **BR-004**: Resultados vindos do cache NÃO são persistidos novamente (já estão no banco).
- **BR-005**: Resultados vindos da web seguem o fluxo normal: validation → persist → timeline → report.

---

## 7. Dependencies

| Dependência | Tipo | Observação |
|-------------|------|------------|
| ChromaDB | Existente | Já configurado em `./db/` |
| `gemini-embedding-2` | Existente | Mesmo modelo usado no persist |
| `langchain-google-genai` | Existente | Já no requirements.txt |
| `GOOGLE_API_KEY` | Existente | Variável já obrigatória |

---

## 8. Risks

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| ChromaDB vazio na primeira execução | Zero resultados → flui para web normalmente | BR-003 garante o fallback |
| Embedding lento aumenta latência mesmo em cache hit | Latência adicional ~1-2s | Aceitável; compensa a busca web (~10s) |
| Resultados de cache desatualizados | Score alto mas conteúdo desatualizado | Threshold configurável permite ajuste fino |
