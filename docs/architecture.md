# Architecture

## Camadas principais

### 1. Scraping
`src/adapters/linkedin` concentra `fetch`, `extract` e `normalize` para vagas do LinkedIn.

### 2. Application services
`src/services` orquestra ingestão, enriquecimento, persistência e rotinas de lote.

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

## Chat mode

- `new_chat`: abre o app base e tenta iniciar um chat limpo
- `existing_chat`: abre uma URL específica de conversa

Para enrichment, `new_chat` é o modo recomendado por previsibilidade.

## Observabilidade

Cada execução pode salvar:

- HTML final em `data/debug/<provider>_page.html`
- screenshot em `data/debug/<provider>_page.png`
- log em JSON lines em `data/ai_responses_log.json`

## Decisões importantes

### Por que enrichment web não substitui tudo?
Providers web são úteis, mas têm custos operacionais maiores:
- DOM pode mudar
- resposta pode vir fora do formato
- são mais lentos que API
- dependem de sessão autenticada

Por isso o projeto mantém `groq` como provider natural de API e usa providers web como alternativa configurável.
