# Architecture

## Camadas principais

### 1. Scraping

`src/adapters/linkedin` concentra `fetch`, `extract` e `normalize` para vagas do LinkedIn.

A camada também contém componentes específicos para páginas de busca do LinkedIn:

- `search_selectors.py`: seletores e padrões usados na busca
- `search_extractor.py`: transformação de payloads de cards em objetos estruturados
- `search_fetcher.py`: abertura da busca, scroll incremental, captura de cards e complemento de vagas parciais

### 2. Application services

`src/services` orquestra ingestão, enriquecimento, persistência e rotinas de lote.

Serviços relevantes:

- `ingest_service.py`: pipeline base de ingestão por URL
- `linkedin_search_collection_service.py`: coleta/auditoria de buscas do LinkedIn
- `linkedin_search_ingest_service.py`: ingestão das vagas coletadas usando o mesmo pipeline de `ingest-url`
- `ai_enrichment_service.py`: enriquecimento por IA
- `browser_ai_service.py`: sessão de providers web

### 3. Browser AI

`src/adapters/ai_web` concentra integrações web para ChatGPT e Gemini.

Essa camada foi isolada do scraping porque lida com um domínio diferente:

- automação de conversas
- perfis persistentes
- retries
- seletores
- extração incremental de resposta
- logs operacionais

### 4. API

`src/api` expõe os endpoints FastAPI.

Endpoints relevantes:

- `POST /ingest-url`: ingestão individual de vaga por URL
- `POST /ingest-csv`: ingestão em lote a partir de CSV
- `POST /linkedin/search-jobs/collect`: coleta/auditoria de busca LinkedIn
- `POST /linkedin/search-jobs/collect-ingest`: coleta e ingestão das vagas abertas encontradas na busca

### 5. Data layer

`src/db` define modelos, base e sessão.

## Fluxos principais

### Ingestão individual

1. receber URL
2. resolver adapter
3. buscar página
4. extrair payload
5. normalizar
6. persistir

### Ingestão por CSV em lote

1. ler CSV
2. filtrar por `status`
3. normalizar linhas
4. processar URLs uma por vez
5. reutilizar a mesma sessão do navegador
6. persistir e registrar resultado por item

### Coleta de busca LinkedIn

1. abrir uma URL de busca autenticada no LinkedIn
2. rolar a lista lateral incrementalmente
3. extrair cards visíveis a cada rolagem
4. deduplicar por `linkedin_job_id` ou URL
5. detectar vagas fechadas/expiradas
6. completar cards parciais abrindo a URL individual da vaga
7. exportar Excel, HTML e screenshot para auditoria

### Coleta + ingestão de busca LinkedIn

1. executar a coleta de busca
2. ignorar vagas fechadas por padrão
3. para cada vaga aberta, chamar o pipeline de ingestão por URL
4. reutilizar adapter/fetcher com sessão autenticada
5. persistir ou atualizar a vaga na tabela `Job`
6. retornar resumo de processadas, sucesso, falhas e ignoradas

### Enrichment por API

1. buscar vagas pendentes
2. aplicar blocklist e filtros
3. montar contexto
4. chamar provider configurado
5. validar saída
6. persistir campos enriquecidos

### Enrichment web

Quando `enrichment_provider` é `chatgpt_web` ou `gemini_web`, o fluxo passa por:

- `src/services/ai_enrichment_service.py`
- `src/services/browser_ai_service.py`
- `src/adapters/ai_web/...`

O serviço monta um prompt estruturado, executa a automação web, extrai JSON, normaliza campos problemáticos e só então valida e persiste.

## Browser AI design

Cada provider segue o mesmo contrato:

- `AIChatOptions`: modo de execução, timeout e retries
- `AIResponse`: saída estruturada com `text`, `provider`, `chat_url`, `success`, `metadata` e `error`
- `BaseAIWebFetcher`: navegação, retry, debug e extração incremental
- `BaseAIWebAdapter`: persistência do log e interface padronizada
- `AIAdapterFactory`: resolve `chatgpt` e `gemini`

## LinkedIn Search design

A busca do LinkedIn é tratada como uma etapa de descoberta de URLs, não como substituto do pipeline de ingestão.

Decisão principal:

```text
LinkedIn search
→ descobrir cards/URLs
→ completar dados mínimos para auditoria
→ chamar o mesmo extractor/pipeline de ingest-url
→ persistir na tabela Job
```

Essa separação reduz duplicação e mantém um único caminho de normalização/persistência.

## Chat mode

- `new_chat`: abre o app base e tenta iniciar um chat limpo
- `existing_chat`: abre uma URL específica de conversa

Para enrichment, `new_chat` é o modo recomendado por previsibilidade.

## Observabilidade

Cada execução pode salvar:

- HTML final em `data/debug/<provider>_page.html`
- screenshot em `data/debug/<provider>_page.png`
- log em JSON lines em `data/ai_responses_log.json`

A busca LinkedIn salva artefatos como:

- `data/debug/linkedin_search_<timestamp>.html`
- `data/debug/linkedin_search_<timestamp>.png`
- `data/exports/linkedin_search_cards.xlsx`

## Decisões importantes

### Por que a busca LinkedIn não grava automaticamente sempre?

Porque o modo de auditoria é útil para validar:

- qualidade da captura
- quantidade de cards encontrados
- vagas expiradas
- cards parciais
- mudanças de DOM do LinkedIn

Por isso o script mantém o comportamento seguro por padrão e só grava com `--ingest`.

### Por que enrichment web não substitui tudo?

Providers web são úteis, mas têm custos operacionais maiores:

- DOM pode mudar
- resposta pode vir fora do formato
- são mais lentos que API
- dependem de sessão autenticada

Por isso o projeto mantém `groq` como provider natural de API e usa providers web como alternativa configurável.
