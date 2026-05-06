# Project Configuration

---

## Project Vision

```yaml
vision:
  summary: "Um workflow de pesquisa inteligente com LangGraph que automatiza buscas na internet, valida qualidade dos resultados e gera relatórios estruturados em HTML"

  target_users:
    - "Pesquisador/Desenvolvedor: Precisa de pesquisas aprofundadas e organizadas na internet de forma automatizada"

  value_proposition: |
    Automatiza o processo de pesquisa na internet usando agentes especializados,
    garantindo qualidade dos resultados, rastreabilidade dos passos e um relatório
    final estruturado com referências.

  principles:
    - "Transparência: Cada passo da pesquisa é registrado com data/hora e contexto"
    - "Qualidade sobre quantidade: Resultados são ranqueados por relevância ao objetivo"
    - "Output acionável: Relatório HTML pronto para uso com links de referência"

  anti_goals:
    - "Não é uma ferramenta de scraping em massa"
    - "Não substitui buscas que requerem login/autenticação em sites"
```

---

## Default Feature Settings

```yaml
defaults:
  project_type: mvp
  ltp_enabled: false
  execution_strategy: sequential
  user_profile: technical
```

---

```yaml
overrides: []
```
