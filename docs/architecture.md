# Architecture

## Camadas principais

### 1. Scraping
`src/adapters/linkedin` concentra fetch, extract e normalize para vagas do LinkedIn.

### 2. Application services
`src/services` orquestra ingestão, enriquecimento e persistência.

### 3. Browser AI
`src/adapters/ai_web` concentra integrações web para ChatGPT e Gemini.

Essa camada foi isolada do scraping porque lida com um domínio diferente: automação de conversas, perfis persistentes, retries, seletores e captura de resposta.

### 4. API
`src/api` expõe os endpoints FastAPI.

### 5. Data layer
`src/db` define modelos, base e sessão.

## Browser AI design

Cada provider segue o mesmo contrato:

- `AIChatOptions`: modo de execução e timeout
- `AIResponse`: saída estruturada
- `BaseAIWebFetcher`: navegação, retry, debug e extração incremental
- `BaseAIWebAdapter`: persistência do log e interface padronizada

## Chat mode

- `new_chat`: abre o app base e tenta iniciar um chat limpo
- `existing_chat`: abre uma URL específica de conversa

`new_chat` é o modo recomendado para testes determinísticos.

## Observabilidade

Cada execução salva:

- HTML final em `data/debug/<provider>_page.html`
- screenshot em `data/debug/<provider>_page.png`
- log em JSON lines em `data/ai_responses_log.json`
