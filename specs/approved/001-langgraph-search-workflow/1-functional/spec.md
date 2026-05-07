# LangGraph Search Workflow - Functional Spec

**Status**: approved
**Owner**: jardel.kuhnen@mercadolivre.com
**Created**: 2026-05-06
**Last Updated**: 2026-05-06

---

## Problem Statement

Pesquisas manuais na internet são fragmentadas: o usuário precisa abrir múltiplas abas, avaliar credibilidade de fontes, comparar informações e montar um relatório. Não há rastreabilidade do processo nem ranking objetivo dos resultados.

**Impacto**: Tempo excessivo por pesquisa, resultados inconsistentes e sem estrutura para compartilhamento ou reprodução.

---

## Objectives

1. Automatizar pesquisas na internet via CLI usando agentes LangGraph especializados
2. Entregar resultados ranqueados por qualidade (relevância, credibilidade, recência e profundidade)
3. Registrar rastreabilidade completa do processo de pesquisa (timeline)
4. Gerar relatório HTML pronto para uso com links de referência, auto-aberto no browser

---

## Scope

### In Scope
- Workflow LangGraph com 4 agentes especializados (Busca, Validação/Ranking, Timeline, Relatório HTML)
- Pesquisa via Tavily API em sites específicos ou na internet toda
- Especificação de sites via `--sites` flag (domínios) ou `--sites-group` (grupos do arquivo `sites.yaml`). Em caso de não houver configuração de sites, a pesquisa deverá ser realizada na internet aberta.
- Ranqueamento com score 0-100 por relevância, credibilidade da fonte, recência e profundidade
- Timeline de rastreabilidade com timestamp, agente, site e filtros de cada passo
- Relatório HTML salvo localmente e auto-aberto no browser padrão
- 5 resultados por pesquisa Tavily (MVP)
- LLM configurável via variável de ambiente (No mvp vamos utilizar gemini como llm)

### Out of Scope
- Pesquisas em sites que requerem login/autenticação
- Múltiplas rodadas iterativas de refinamento automático
- Histórico de pesquisas anteriores
- Interface gráfica (somente CLI)
- Exportação em outros formatos (PDF, Markdown)
- Streaming/progresso em tempo real dos agentes

---

## User Stories

### US-1: Executar pesquisa geral via CLI

**As a** pesquisador,
**I want** executar `python main.py --query="minha pergunta"`,
**So that** eu receba um relatório completo de pesquisa sem configuração prévia.

**Acceptance Criteria**:
- `--query` é obrigatório; se ausente, exibe mensagem de uso e encerra com código de erro 1
- O workflow executa todos os 4 agentes em sequência exibindo progresso: `[1/4] Search Agent...`
- Sem `--sites` nem `--sites-group`, a busca é feita na internet toda (5 resultados gerais via Tavily)
- Ao final, um arquivo HTML é salvo e aberto automaticamente no browser padrão
- O caminho do arquivo gerado é exibido no terminal ao final da execução

**Priority**: High

---

### US-2: Pesquisa em sites específicos via CLI

**As a** pesquisador,
**I want** usar `--sites="site1.com,site2.com"` para direcionar a pesquisa,
**So that** eu obtenha resultados apenas das fontes que me interessam.

**Acceptance Criteria**:
- `--sites` aceita lista separada por vírgulas de domínios (ex: `mercadolivre.com.br,amazon.com.br`)
- Cada site recebe uma busca Tavily separada com filtro de domínio, retornando até 5 resultados
- Se um site não retornar resultados, é registrado na timeline com status "sem resultados" e o workflow continua
- `--sites` tem prioridade sobre `--sites-group` quando ambos são informados

**Priority**: High

---

### US-3: Grupos de sites pré-definidos por arquivo de config

**As a** pesquisador,
**I want** criar um arquivo `sites.yaml` com grupos de sites por categoria e usar `--sites-group=nome`,
**So that** eu reutilize listas de sites sem redigitar domínios a cada execução.

**Acceptance Criteria**:
- `sites.yaml` na raiz do projeto define grupos com estrutura: `groups: { nome: [domínio1, domínio2] }`
- `--sites-group=ecommerce` seleciona o grupo correspondente do arquivo
- Se o arquivo `sites.yaml` não existir e `--sites-group` for usado, exibe erro claro e encerra com código 1
- Se o grupo especificado não existir no arquivo, exibe os grupos disponíveis e encerra com código 1

**Priority**: Medium

---

### US-4: Resultados ranqueados por score de qualidade

**As a** pesquisador,
**I want** receber os resultados ordenados por score de qualidade,
**So that** eu foque no que é mais relevante e confiável para minha pesquisa.

**Acceptance Criteria**:
- Cada resultado recebe score de 0-100 composto por 4 critérios com peso igual (25% cada): relevância ao objetivo, credibilidade da fonte, recência e profundidade do conteúdo
- Resultados são apresentados do maior para o menor score no relatório HTML
- Resultados com score < 40 recebem badge visual "baixa relevância" no HTML
- O score e a contribuição de cada critério são visíveis no relatório HTML

**Priority**: High

---

### US-5: Timeline de rastreabilidade do processo

**As a** pesquisador,
**I want** visualizar o histórico de cada passo da pesquisa,
**So that** eu entenda como o resultado foi construído e possa reproduzir a pesquisa.

**Acceptance Criteria**:
- Cada evento registra: timestamp ISO-8601, agente executor, ação realizada, site alvo (quando aplicável) e query/filtros usados
- Eventos mínimos obrigatórios: início do workflow, cada chamada Tavily, início da validação, início da geração do HTML, caminho do arquivo gerado
- A timeline é exibida no terminal ao final da execução (formato texto simples)
- A timeline é incluída como seção no relatório HTML

**Priority**: High

---

### US-6: Relatório HTML com referências e auto-abertura no browser

**As a** pesquisador,
**I want** receber um arquivo HTML bem estruturado que abra automaticamente no browser,
**So that** eu consulte, compartilhe e acesse as fontes de pesquisa diretamente.

**Acceptance Criteria**:
- Arquivo salvo como `search_YYYYMMDD_HHMMSS.html` no diretório de execução
- Auto-abre no browser padrão ao terminar; se falhar, exibe o caminho no terminal como fallback
- Conteúdo mínimo do HTML: header (query, data/hora, total de resultados), lista de resultados ranqueados (título, URL clicável, snippet, score, badges), seção de timeline, footer com links de referência agrupados por site
- CSS inline no HTML (sem dependências externas — funciona offline)

**Priority**: High

---

## User Experience

### Fluxo Principal (CLI)

```
$ python main.py --query="cadeiras ergonômicas para 1,93 de altura"

[1/4] Search Agent        → Buscando "cadeiras ergonômicas para 1,93 de altura"...
[2/4] Validation Agent    → Ranqueando 5 resultados...
[3/4] Timeline Agent      → Compilando timeline (7 eventos)...
[4/4] Report Agent        → Gerando HTML...

✅ Concluído em 23s
📄 Relatório: ./search_20260506_143022.html (aberto no browser)

Timeline:
  14:30:15 | Search Agent     | Busca geral | query: "cadeiras ergonômicas..." | 5 resultados
  14:30:22 | Validation Agent | Ranking     | 5 resultados processados
  14:30:28 | Report Agent     | HTML gerado | ./search_20260506_143022.html
```

### Fluxo com Sites Específicos

```
$ python main.py --query="cadeiras ergonômicas" --sites="mercadolivre.com.br,amazon.com.br"

[1/4] Search Agent → Buscando em 2 sites...
  - mercadolivre.com.br: 5 resultados
  - amazon.com.br: 3 resultados
...
```

---

## Success Metrics

1. Workflow completo em < 60 segundos para pesquisa geral (5 resultados, internet toda)
2. Score calculado e visível para 100% dos resultados retornados
3. Timeline com todos os eventos obrigatórios registrados (0 eventos faltando)
4. HTML válido gerado e auto-aberto no browser sem erros
5. Erros de configuração (API key ausente, grupo inexistente) comunicados claramente com código de saída != 0

---

## Business Rules

- **Máximo 5 resultados por chamada Tavily**: para múltiplos sites, 5 por site; para internet geral, 5 no total
- **Timeout Tavily**: 30 segundos por chamada; timeout é registrado na timeline, workflow continua com resultados já obtidos
- **Timeout LLM**: 60 segundos por chamada; se ultrapassar, registra na timeline e usa fallback (score neutro 50 para critério afetado)
- **Arquivo HTML**: nome inclui timestamp com segundos, sobrescrita improvável; em caso de colisão, sobrescreve sem erro
- **Query vazia ou só espaços**: encerra com código 1 antes de iniciar o workflow

---

## Dependencies

- Tavily API (requer `TAVILY_API_KEY` no ambiente)
- LLM via LangChain (requer API key do provider configurado via `.env`)
- LangGraph para orquestração
- Python 3.11+

---

## Risks

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Tavily API indisponível | Baixa | Alto | Erro claro com código de saída 1 e instrução para verificar API key |
| LLM com latência alta | Média | Médio | Timeout de 60s por chamada; score fallback 50 para critério afetado |
| Site sem resultados via Tavily | Alta | Baixo | Registrar na timeline, continuar com demais sites |
| HTML não abre no browser | Baixa | Baixo | Exibir caminho do arquivo no terminal como fallback |

---

## Critical E2E Test Scenarios

> MVP: LTP desabilitado. Cenários documentados para validação manual.

### E2E Test Summary

| ID | Cenário | Criticidade | US Relacionada |
|----|---------|-------------|----------------|
| E2E-1 | Pesquisa geral bem-sucedida | 🔴 Crítico | US-1, US-4, US-5, US-6 |
| E2E-2 | Pesquisa com sites específicos | 🔴 Crítico | US-2, US-5 |
| E2E-3 | Grupo de sites via sites.yaml | 🟡 Importante | US-3 |
| E2E-4 | Erro - query ausente | 🟡 Importante | US-1 |

---

### E2E-1: Pesquisa geral bem-sucedida

**Input**: `python main.py --query="cadeiras ergonômicas 1,93"`

**Resultado esperado**:
- HTML gerado com nome `search_YYYYMMDD_HHMMSS.html` no diretório atual
- HTML auto-aberto no browser
- 5 resultados ranqueados por score decrescente
- Timeline com todos os eventos obrigatórios registrados

---

### E2E-2: Pesquisa com sites específicos

**Input**: `py