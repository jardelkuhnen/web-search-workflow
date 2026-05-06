#!/usr/bin/env python3
"""LangGraph Search Workflow — CLI entry point."""

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _load_sites_from_group(group_name: str) -> list[str]:
    """Load sites from sites.yaml for the given group name."""
    import yaml

    yaml_path = Path(__file__).parent / "sites.yaml"
    if not yaml_path.exists():
        print(f"Erro: arquivo sites.yaml não encontrado. Crie-o na raiz do projeto.", file=sys.stderr)
        sys.exit(1)

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    groups = data.get("groups", {})
    if group_name not in groups:
        available = ", ".join(groups.keys())
        print(
            f"Erro: grupo '{group_name}' não encontrado em sites.yaml.\n"
            f"Grupos disponíveis: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    return [str(s) for s in groups[group_name]]


def main():
    parser = argparse.ArgumentParser(
        description="LangGraph Search Workflow — pesquisa automatizada na internet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py --query="cadeiras ergonômicas"
  python main.py --query="tênis running" --sites="mercadolivre.com.br,amazon.com.br"
  python main.py --query="python async" --sites-group=tech
        """,
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Pergunta ou termos de busca (obrigatório)",
    )
    parser.add_argument(
        "--sites",
        default=None,
        help="Lista de domínios separados por vírgula (ex: site1.com,site2.com)",
    )
    parser.add_argument(
        "--sites-group",
        default=None,
        dest="sites_group",
        help="Nome do grupo de sites definido em sites.yaml",
    )

    args = parser.parse_args()

    query = args.query.strip()
    if not query:
        print("Erro: --query não pode ser vazio.", file=sys.stderr)
        sys.exit(1)

    # Validate API keys before starting
    if not os.environ.get("TAVILY_API_KEY"):
        print(
            "Erro: TAVILY_API_KEY não configurada. Adicione ao arquivo .env e tente novamente.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.environ.get("GOOGLE_API_KEY"):
        print(
            "Erro: GOOGLE_API_KEY não configurada. Adicione ao arquivo .env e tente novamente.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve sites
    sites: list[str] = []
    sites_group: str | None = None

    if args.sites:
        # --sites has priority over --sites-group
        sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    elif args.sites_group:
        sites_group = args.sites_group
        sites = _load_sites_from_group(sites_group)

    # Build and run the workflow
    from workflow.graph import build_graph
    from workflow.agents.timeline_agent import format_timeline_for_terminal

    graph = build_graph()

    print(f'\nIniciando pesquisa: "{query}"')
    if sites:
        print(f"Sites: {', '.join(sites)}")
    print()

    start = time.time()

    initial_state = {
        "query": query,
        "sites": sites,
        "sites_group": sites_group,
        "raw_results": [],
        "ranked_results": [],
        "timeline": [],
        "html_path": None,
        "errors": [],
        "workflow_start": None,
    }

    final_state = graph.invoke(initial_state)

    elapsed = time.time() - start

    # Check for errors
    errors = final_state.get("errors", [])
    if errors:
        for err in errors:
            print(f"[!] {err}", file=sys.stderr)
        sys.exit(1)

    html_path = final_state.get("html_path")
    print(f"\n✅ Concluído em {elapsed:.0f}s")
    if html_path:
        print(f"📄 Relatório: {html_path} (aberto no browser)")
    else:
        print("⚠️  Nenhum relatório HTML gerado.")

    # Print timeline
    timeline = final_state.get("timeline", [])
    if timeline:
        print("\nTimeline:")
        print(format_timeline_for_terminal(timeline))


if __name__ == "__main__":
    main()
