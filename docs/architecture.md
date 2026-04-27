# Architecture

## Camadas principais

### 1. Scraping
`src/adapters/linkedin` concentra fetch, extract e normalize para vagas do LinkedIn.

### 2. Application services
`src/services` orquestra ingestão, enriquecimento, importação em lote e persistência.

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

## Ingestão individual e em lote

A arquitetura de ingestão agora possui dois fluxos compatíveis:

### Ingestão individual
Entrada por URL única via endpoint `POST /ingest-url`, usada por scripts e automações pontuais.

### Ingestão em lote por CSV
Entrada por endpoint dedicado e por script Python/PowerShell, com as seguintes etapas:

1. leitura do CSV
2. filtro por status configurável
3. normalização do payload para `IngestUrlRequest`
4. deduplicação básica por identificador externo ou URL
5. processamento sequencial em uma única sessão Playwright
6. persistência e relatório por item

## Componentes do batch import

- `src/services/jobs_csv_import_service.py`: leitura, validação e mapeamento do CSV
- `src/services/batch_ingest_service.py`: execução em lote e agregação de resultados
- `src/adapters/linkedin/fetcher.py`: sessão reutilizável do navegador para múltiplas URLs
- `src/api/routes_jobs.py`: endpoints de ingestão individual e em lote
- `scripts/import_jobs_csv.py`: execução local via CLI
- `scripts/powershell/run_api_posts_from_csv.ps1`: runner operacional no Windows

## Observabilidade

Cada execução de browser AI salva:

- HTML final em `data/debug/<provider>_page.html`
- screenshot em `data/debug/<provider>_page.png`
- log em JSON lines em `data/ai_responses_log.json`

A execução de batch import deve registrar, por item:

- URL
- identificador externo
- status final
- mensagem de erro, quando houver
- timestamp do processamento
