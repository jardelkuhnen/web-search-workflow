# LangGraph Search Workflow

Workflow automatizado de pesquisa na internet usando [LangGraph](https://github.com/langchain-ai/langgraph), [Tavily](https://tavily.com/) e Google Gemini. Realiza buscas, ranqueia resultados e gera um relatório HTML com timeline de execução.

## Como funciona

1. Recebe uma query e opcionalmente uma lista de sites
2. Usa Tavily para buscar resultados na web
3. Usa Google Gemini para ranquear e sumarizar os resultados
4. Gera um relatório HTML e o abre no browser

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

| Grupo      | Sites                                                        |
|------------|--------------------------------------------------------------|
| `ecommerce`| mercadolivre.com.br, amazon.com.br, shopee.com.br, americanas.com.br |
| `news`     | g1.globo.com, folha.uol.com.br, uol.com.br, bbc.com/portuguese |
| `tech`     | tecnoblog.net, tudocelular.com, canaltech.com.br, tecmundo.com.br |
| `research` | scholar.google.com, arxiv.org, pubmed.ncbi.nlm.nih.gov       |
| `reddit`   | reddit.com                                                   |

Para adicionar ou editar grupos, edite o arquivo `sites.yaml`.

## Estrutura do projeto

```
search-workflow/
├── main.py           # CLI entry point
├── requirements.txt  # Dependências
├── sites.yaml        # Grupos de sites predefinidos
├── .env              # Variáveis de ambiente (não versionado)
└── workflow/         # Lógica do workflow LangGraph
```
