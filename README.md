# LangGraph Search Workflow

Workflow automatizado de pesquisa na internet usando [LangGraph](https://github.com/langchain-ai/langgraph), [Tavily](https://tavily.com/) e Google Gemini. Consulta primeiro um cache semântico local (ChromaDB) antes de acionar a busca na web, reduzindo latência e consumo de API em consultas recorrentes ou semanticamente similares.

## Como funciona

### Fluxo completo

```
retriever → validation → [router]
                           ├── cache hit  → timeline → report
                           └── cache miss → search → validation → persist → timeline → report
```

1. **Retriever Agent** — embeda a query com `gemini-embedding-2` e consulta o ChromaDB local
2. **Validation Agent** — ranqueia os resultados (cache ou web) com score 0–100 via Gemini
3. **Router condicional** — decide com base no score e no flag `web_searched`:
   - `score >= threshold` e ainda não buscou na web → **cache hit**, pula a busca
   - `score < threshold` ou ChromaDB vazio → **cache miss**, aciona busca na web
   - já buscou na web → **persist**, salva os novos resultados no ChromaDB
4. **Search Agent** — busca na web via Tavily (acionado apenas em cache miss)
5. **Persist Agent** — salva os resultados da web no ChromaDB para consultas futuras
6. **Timeline Agent** — consolida todos os eventos de execução
7. **Report Agent** — gera relatório HTML e abre no browser

## Pré-requisitos

- Python 3.12+
- Conta no [Tavily](https://tavily.com/) (API key gratuita disponível)
- Conta no [Google AI Studio](https://aistudio.google.com/) (API key do Gemini)

## Instalação

```bash
# Clone o repositório
git clone <repo-url>
cd search-workflow

# Crie o venv e instale as dependências (via Makefile)
make setup
```

Ou manualmente:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Importante:** sempre ative o venv antes de usar `pip install`, ou use `make install`. Sem isso, o pip pode instalar no ambiente global e causar conflitos.

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Score mínimo (escala 0-10) para aceitar resultados do ChromaDB sem busca na web.
# Abaixo deste valor, o workflow realiza busca na web normalmente.
# Default: 7
RETRIEVAL_SCORE_THRESHOLD=7
```

## Uso

### Busca simples

```bash
make run ARGS='--query="cadeiras ergonômicas"'
# ou diretamente:
.venv/bin/python main.py --query="cadeiras ergonômicas"
```

### Busca em sites específicos

```bash
.venv/bin/python main.py --query="tênis running" --sites="mercadolivre.com.br,amazon.com.br"
```

### Busca usando grupo de sites predefinido

```bash
.venv/bin/python main.py --query="python async" --sites-group=tech
```

### Grupos disponíveis (`sites.yaml`)

| Grupo       | Sites                                                               |
|-------------|---------------------------------------------------------------------|
| `ecommerce` | mercadolivre.com.br, amazon.com.br, shopee.com.br, americanas.com.br |
| `news`      | g1.globo.com, folha.uol.com.br, uol.com.br, bbc.com/portuguese     |
| `tech`      | tecnoblog.net, tudocelular.com, canaltech.com.br, tecmundo.com.br  |
| `research`  | scholar.google.com, arxiv.org, pubmed.ncbi.nlm.nih.gov             |
| `reddit`    | reddit.com                                                          |

Para adicionar ou editar grupos, edite o arquivo `sites.yaml`.

## Cache semântico (ChromaDB)

O workflow mantém um banco vetorial local em `./db/`. A cada execução:

- Resultados já armazenados são recuperados por similaridade semântica da query
- Se o melhor score for `>= RETRIEVAL_SCORE_THRESHOLD`, o resultado vem do cache (sem chamar Tavily)
- Resultados novos (vindos da web) são automaticamente persistidos para uso futuro
- O filtro `--sites` / `--sites-group` é aplicado tanto na busca web quanto na consulta ao cache

O threshold padrão é `7` (escala 0–10). Valores menores tornam o cache mais permissivo; valores maiores forçam mais buscas na web.

## Estrutura do projeto

```
search-workflow/
├── main.py                        # CLI entry point
├── requirements.txt               # Dependências
├── sites.yaml                     # Grupos de sites predefinidos
├── .env                           # Variáveis de ambiente (não versionado)
├── db/                            # Banco vetorial ChromaDB (gerado na primeira execução)
├── core/
│   └── vector_store.py            # Abstração do ChromaDB (add_results, query_results)
├── workflow/
│   ├── state.py                   # Definição do WorkflowState (TypedDict)
│   ├── graph.py                   # Grafo LangGraph e roteamento condicional
│   └── agents/
│       ├── retriever_agent.py     # Consulta semântica ao ChromaDB
│       ├── search_agent.py        # Busca na web via Tavily
│       ├── validation_agent.py    # Ranking de resultados via Gemini
│       ├── persist_agent.py       # Persistência no ChromaDB
│       ├── timeline_agent.py      # Consolidação da timeline
│       └── report_agent.py        # Geração do relatório HTML
└── tests/
    ├── test_vector_store.py       # Testes de query_results()
    ├── test_graph_router.py       # Testes do roteamento condicional
    └── test_persist_agent.py      # Testes do persist_agent e add_results()
```
