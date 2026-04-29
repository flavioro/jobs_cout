# Roadmap

## Entregue recentemente

- camada `ai_web` isolada do scraping
- suporte a ChatGPT e Gemini via browser automation
- importação em lote por CSV com sessão reutilizável
- enrichment por provider configurável
- suporte a `chatgpt_web` e `gemini_web`
- normalização defensiva do payload de enrichment web
- coleta de vagas por URLs de busca do LinkedIn
- scroll incremental em listas virtualizadas do LinkedIn
- exportação Excel/HTML/PNG para auditoria da busca
- detecção de vagas fechadas/expiradas na busca
- complemento de cards parciais usando o extractor do fluxo `ingest-url`
- modo `--ingest` no script de busca LinkedIn para gravar vagas na tabela `Job`
- modo `--dry-run` para simular a ingestão sem gravar no banco
- testes unitários e smoke para a camada `ai_web`
- testes focados para coleta e ingestão da busca LinkedIn

## Curto prazo

- validar deduplicação em execuções repetidas de `--ingest`
- melhorar relatório final da ingestão por busca
- adicionar métricas de performance por etapa
- ampliar troubleshooting operacional dos providers web
- registrar comparativos de qualidade entre `groq`, `chatgpt_web` e `gemini_web`

## Médio prazo

- fallback automático entre providers de enrichment
- suporte a novos providers web
- providers por API oficial quando viável
- dashboards operacionais de ingestão e enrichment
- rotinas agendadas para buscas salvas do LinkedIn

## Longo prazo

- workers assíncronos para pipelines completos
- múltiplas fontes de vagas além do LinkedIn
- automações orientadas por perfil e prioridade de candidatura
- fila de candidatura assistida com priorização por fit
