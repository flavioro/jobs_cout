# Roadmap

## Entregue recentemente

- camada `ai_web` isolada do scraping tradicional
- suporte a ChatGPT e Gemini com contrato comum
- smoke checks e testes unitários para browser AI
- documentação base da arquitetura
- importação em lote por CSV com processamento sequencial em sessão única

## Curto prazo

- reforçar deduplicação por banco antes do batch
- melhorar relatório final por item no importador CSV
- adicionar métricas de performance por etapa
- ampliar cobertura de smoke tests por provider e importação

## Médio prazo

- suporte a novos providers web
- providers por API oficial quando viável
- dashboards operacionais de ingestão, enrichment e batch import
- filtros adicionais para importação CSV por senioridade, work model e origem

## Longo prazo

- workers assíncronos para pipelines completos
- múltiplas fontes de vagas além do LinkedIn
- automações orientadas por perfil e prioridade de candidatura
