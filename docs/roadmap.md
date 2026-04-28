# Roadmap

## Entregue recentemente

- camada `ai_web` isolada do scraping
- suporte a ChatGPT e Gemini via browser automation
- importação em lote por CSV com sessão reutilizável
- enrichment por provider configurável
- suporte a `chatgpt_web` e `gemini_web`
- normalização defensiva do payload de enrichment web
- testes unitários e smoke para a camada `ai_web`

## Curto prazo

- ampliar cobertura de smoke tests por provider
- adicionar métricas de performance por etapa
- melhorar troubleshooting operacional dos providers web
- registrar comparativos de qualidade entre `groq`, `chatgpt_web` e `gemini_web`

## Médio prazo

- fallback automático entre providers
- suporte a novos providers web
- providers por API oficial quando viável
- dashboards operacionais de ingestão e enrichment

## Longo prazo

- workers assíncronos para pipelines completos
- múltiplas fontes de vagas além do LinkedIn
- automações orientadas por perfil e prioridade de candidatura
