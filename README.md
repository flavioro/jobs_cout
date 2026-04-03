# JobScout v1.1 (LinkedIn + SQLite)

Pipeline profissional para ingestão de vagas do LinkedIn por URL direta, com:
- FastAPI
- Pydantic v2
- Playwright
- SQLAlchemy 2.x
- SQLite por padrão
- logging estruturado com structlog
- HTML bruto salvo em disco para auditoria
- payload com campos opcionais de confirmação (`title`, `company`, `location_raw`, `is_easy_apply`, `seniority_hint`, `workplace_type`)
- extração da vaga principal + captura de **Mais vagas** em tabela separada
- status técnico da coleta separado do status funcional da vaga

> **Uso responsável:** o LinkedIn restringe scraping automatizado em seus termos e em seu `robots.txt`. Use este projeto apenas em contextos autorizados, pessoais ou de pesquisa, com volume baixo e uma URL por vez.

## O que esta versão corrige

Esta versão já incorpora os ajustes observados nos HTMLs reais enviados durante a validação:

- limpeza de `location_raw` para remover ruído como `há 1 dia`, `Mais de 100 candidaturas`, `25 pessoas clicaram em Candidate-se`;
- limpeza de `title` quando vier poluído pelo fallback da aba (`| Empresa`, `(Remoto)`, `| LinkedIn`);
- detecção de `workplace_type` a partir do topo **e** da descrição da vaga;
- detecção de vaga fechada por texto como `Não aceita mais candidaturas`;
- separação entre:
  - `status` = resultado técnico da extração;
  - `availability_status` = situação funcional da vaga;
- captura de cards de **Mais vagas** em `related_jobs`, com `canonical_related_job_url` e deduplicação por vaga relacionada;
- novos testes de regressão baseados nos HTMLs reais capturados.

## Estrutura

```text
jobscout/
├── data/
│   ├── debug/
│   ├── raw_html/
│   └── storage_state.json
├── logs/
│   └── powershell/
│       ├── responses/
│       ├── api_posts_summary.json
│       ├── db_tables_run.log
│       ├── db_tables_summary.json
│       ├── db_tables_summary.txt
│       └── pytest.log
├── scripts/
│   ├── login_linkedin.py
│   └── powershell/
│       ├── config.ps1
│       ├── run_all.ps1
│       ├── run_api_posts.ps1
│       ├── run_pytest.ps1
│       ├── show_db_tables.ps1
│       └── start_api.cmd
├── src/
│   ├── adapters/
│   │   ├── base.py
│   │   ├── factory.py
│   │   └── linkedin/
│   │       ├── adapter.py
│   │       ├── extractor.py
│   │       ├── fetcher.py
│   │       └── selectors.py
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes_jobs.py
│   ├── core/
│   │   ├── compare.py
│   │   ├── config.py
│   │   ├── contracts.py
│   │   ├── enums.py
│   │   ├── errors.py
│   │   ├── fingerprint.py
│   │   ├── logging_config.py
│   │   └── normalization.py
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py
│   │   └── session.py
│   ├── schemas/
│   │   └── jobs.py
│   ├── services/
│   │   ├── ingest_service.py
│   │   └── persistence_service.py
│   ├── utils/
│   │   ├── storage.py
│   │   ├── text.py
│   │   └── url.py
│   └── main.py
├── tests/
│   ├── fixtures/
│   │   └── linkedin/
│   ├── conftest.py
│   ├── test_extractor.py
│   ├── test_linkedin_dom_regression_contract.py
│   ├── test_linkedin_extractor_real_pages.py
│   ├── test_linkedin_page_title_fallback.py
│   ├── test_normalization.py
│   └── test_utils.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Requisitos

- Python 3.11+
- Playwright Chromium
- SQLite (já vem embutido no Python)
- opcional: Docker

## Setup local

### 1) Ambiente virtual

**Linux/macOS**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows + Conda**
```bat
call D:\Python\anaconda3\Scripts\activate.bat
conda create -n job_scout python=3.12 -y
conda activate job_scout
```

### 2) Instalar dependências
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 3) Configurar ambiente
```bash
cp .env.example .env
```

### 4) (Opcional) Gerar sessão do LinkedIn
Esse passo salva `data/storage_state.json` para reduzir login repetido.

```bash
python scripts/login_linkedin.py
```

### 5) Subir a API
**Linux/macOS**
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**Windows**
```bat
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

> No Windows, evite `--reload` com Playwright. O modo de recarga automática pode entrar em conflito com subprocessos assíncronos do browser.

### 6) Testar healthcheck
```bash
curl http://127.0.0.1:8000/health
```

## Endpoint principal

### `POST /ingest-url`

Payload:
```json
{
  "url": "https://www.linkedin.com/jobs/view/1234567890/",
  "title": "Desenvolvedor Python Pleno",
  "company": "Empresa Exemplo",
  "location_raw": "Brasil (Remoto)",
  "is_easy_apply": true,
  "seniority_hint": "pleno",
  "workplace_type": "remote"
}
```

Resposta típica:
```json
{
  "status": "success",
  "source": "linkedin",
  "job_id": "c4d6e4c2-ef1f-4d1e-86cc-8b4f61c6a9db",
  "parser_version": "linkedin_v1.1",
  "confirmation": {
    "title": "match",
    "company": "match",
    "location_raw": "normalized_match",
    "is_easy_apply": "match",
    "seniority_hint": "mismatch",
    "workplace_type": "match"
  },
  "job": {
    "title": "Desenvolvedor Python Pleno",
    "company": "Empresa Exemplo",
    "location_raw": "Brasil",
    "is_easy_apply": true,
    "seniority_normalized": "mid",
    "workplace_type": "remote",
    "availability_status": "open",
    "closed_reason": null,
    "apply_url": "https://...",
    "related_jobs_count": 12
  }
}
```

## Endpoints adicionais


### `GET /related-jobs`

Lista todas as vagas relacionadas já persistidas, com filtros opcionais via query string.

Exemplo:
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/related-jobs?limit=50&offset=0' \
  -H 'accept: application/json' \
  -H 'x-api-key: changeme'
```

Filtros disponíveis:
- `parent_job_id`
- `company`
- `workplace_type`
- `is_easy_apply`
- `limit`
- `offset`

Resposta típica:
```json
{
  "items": [
    {
      "id": "uuid",
      "parent_job_id": "uuid",
      "title": "Desenvolvedor Python",
      "company": "Empresa X",
      "related_url": "https://www.linkedin.com/jobs/view/123",
      "location_raw": "Brasil",
      "workplace_type": "remote",
      "is_easy_apply": true,
      "posted_text_raw": "há 2 dias",
      "candidate_signal_raw": "Mais de 100 candidaturas",
      "created_at": "2026-04-03T13:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

- `GET /health`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `GET /related-jobs`
- `GET /jobs/{job_id}/related`

## Regras importantes do modelo

### 1) Verdade primária dos dados
Os campos opcionais do request são apenas **hints** de confirmação. O projeto:
1. coleta a página,
2. extrai os campos,
3. normaliza,
4. compara com os hints,
5. registra `match`, `normalized_match`, `mismatch`, `missing` ou `user_provided_hint`.

### 2) Status técnico vs status funcional
- `status` = qualidade técnica da extração (`success`, `partial`, etc.)
- `availability_status` = estado da vaga (`open`, `closed`, `unknown`)
- `closed_reason` = motivo conhecido quando a vaga estiver fechada (`does_not_accept_applications`, etc.)

### 3) Related jobs
Os cards de **Mais vagas** são extraídos e persistidos em `related_jobs`. Isso permite:
- guardar oportunidades correlatas;
- testar layouts reais do LinkedIn;
- preparar descoberta assistida para uma próxima etapa sem entrar em scraping em massa.

### 4) SQLite na v1
A v1 usa SQLite por padrão para simplificar o setup e acelerar o desenvolvimento.

Exemplo atual:
```env
DATABASE_URL=sqlite+aiosqlite:///./data/jobscout.db
```

## Matriz de validação atual

### Pontos já validados com HTMLs reais
- correção da atribuição de `company` e `location_raw` nos cards laterais verificados;
- regra de sanidade para evitar `company == title` em `related_jobs`;
- `canonical_related_job_url` derivada de `related_external_id` para deduplicação por vaga relacionada;
- limpeza de `title` sem poluição por `| Empresa`, `| LinkedIn` ou `(Remoto)`;
- limpeza de `location_raw` removendo tempo relativo, compartilhamento e volume de candidaturas;
- detecção de `workplace_type` para cenários `remote`, `onsite` e `hybrid`;
- detecção de vaga fechada via `availability_status=closed` e `closed_reason=does_not_accept_applications`;
- suporte a `apply_url` externo quando a vaga redireciona para Gupy, Factorial ou Quickin;
- suporte a `is_easy_apply=true` quando a candidatura simplificada aparece na vaga principal;
- extração de cards laterais de `Mais vagas` para a tabela `related_jobs`;
- regressão com fixtures reais para as vagas `4383830220`, `4392892148`, `4396673137`, `4396458716` e `4392808079`.

### Pontos explicitamente fora de escopo nesta versão
- tratamento de problemas de encoding UTF-8 gerados por scripts externos de export das respostas JSON;
- descoberta automática em massa a partir dos cards de `Mais vagas`;
- LLM no caminho crítico do parser.

### Pontos mapeados para continuar validando e ir removendo do README
- revisar mais casos de `workplace_type` em vagas fechadas para reduzir falso positivo por heurística textual;
- ampliar a cobertura de `availability_status` para outros motivos além de `does_not_accept_applications`;
- validar se todos os cards de `related_jobs` preservam `posted_text_raw` e `candidate_signal_raw` nos layouts alternativos;
- avaliar persistência opcional de sinais brutos adicionais dos cards laterais caso o LinkedIn mude o layout.

## Testes e automação de validação no Windows

Para facilitar a validação local no Windows com Conda, foi adicionada uma rotina automatizada em `scripts/powershell/`.

### Scripts adicionados

- `start_api.cmd`: sobe a API usando o ambiente Conda `job_scout`.
- `config.ps1`: centraliza caminhos, URL base, porta, API key e URLs de vagas.
- `run_pytest.ps1`: executa `pytest -v` e grava saída em log.
- `run_api_posts.ps1`: chama o endpoint `POST /ingest-url` para uma lista de vagas reais e salva as respostas JSON.
- `show_db_tables.ps1`: inspeciona o SQLite e gera um resumo com as tabelas e quantidades de registros.
- `run_all.ps1`: orquestra o fluxo completo de validação.

### Fluxo do `run_all.ps1`

Ao executar o orquestrador, o processo faz:

1. valida a existência dos scripts necessários;
2. abre uma nova janela do CMD e sobe a API com `start_api.cmd`;
3. espera o endpoint `GET /health` responder;
4. executa `pytest -v`;
5. executa os POSTs de validação no endpoint `/ingest-url` com header `x-api-key`;
6. inspeciona o banco SQLite e mostra as tabelas com suas contagens.

### Subir a API manualmente

```bat
scripts\powershell\start_api.cmd
```

### Executar apenas os testes unitários

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\run_pytest.ps1
```

### Executar apenas os POSTs de validação

> Requer a API já rodando em `http://127.0.0.1:8000`.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\run_api_posts.ps1
```

### Executar a inspeção do banco

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\show_db_tables.ps1
```

### Executar tudo de uma vez

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\run_all.ps1
```

### Vagas usadas na validação funcional atual

O fluxo automatizado envia requisições para estas URLs:

- `https://www.linkedin.com/jobs/view/4383830220`
- `https://www.linkedin.com/jobs/view/4392892148`
- `https://www.linkedin.com/jobs/view/4396673137`

### Logs gerados

Os scripts gravam artefatos em `logs/powershell/`, por exemplo:

- `pytest.log`
- `api_posts_summary.json`
- `db_tables_run.log`
- `db_tables_summary.json`
- `db_tables_summary.txt`
- `responses/post_1_*.json`, `responses/post_2_*.json`, `responses/post_3_*.json`

Esses arquivos são temporários de execução local e não devem ser versionados.

## Rodando os testes
```bash
pytest
```

A suíte já cobre:
- regressão com HTMLs reais do LinkedIn;
- fallback do título da aba;
- limpeza de `location_raw`;
- detecção de vaga fechada;
- mapeamento de `workplace_type` a partir da descrição e dos metadados;
- related jobs;
- deduplicação básica dos cards laterais;
- prevenção do bug de senioridade em termos como `internas` vs `intern`;
- caso real adicional para `hybrid`.

## Debug local

Ao executar a coleta, o projeto salva evidências em `data/debug/`:
- `final_url.txt`
- `page_title.txt`
- `linkedin_page.html`
- `linkedin_page.png`

Isso ajuda a revisar mudanças de layout antes de alterar o parser.

## Banco de dados

Tabelas principais:
- `jobs`
- `related_jobs`

> Como esta versão ainda não usa Alembic, se você já tiver um banco antigo em SQLite e quiser refletir as colunas/tabelas novas, o caminho mais simples é apagar `data/jobscout.db` e deixar o projeto recriar o schema no startup.

## Docker

### Subir com Docker
```bash
docker compose up --build
```

A aplicação ficará disponível em:
- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

## Itens já mapeados no README para validação contínua

A ideia aqui é manter os pontos conhecidos documentados e ir retirando do README conforme ficarem plenamente validados no projeto.

### Já implementados nesta versão
- [x] Limpeza de `location_raw`
- [x] Limpeza de `title` via fallback da aba
- [x] Detecção de `workplace_type` por topo e descrição
- [x] Detecção de `availability_status` / `closed_reason`
- [x] Captura e persistência de `related_jobs`
- [x] Endpoint global `GET /related-jobs` com filtros e paginação simples
- [x] Testes reais com HTMLs de debug
- [x] Tratamento de placeholder em `seniority_raw`
- [x] Automação local de validação no Windows com PowerShell
- [x] Inspeção automatizada das tabelas do SQLite

### Mapeados para observar e validar melhor nas próximas execuções
- [ ] Refinar ainda mais `workplace_type` em layouts alternativos do LinkedIn
- [ ] Melhorar captura de `apply_url` em cenários com botão externo variando por idioma/layout
- [ ] Aumentar cobertura para casos com `Presencial` e `Híbrido` reais em fixtures locais
- [ ] Adicionar Alembic para migrações em vez de reset manual do SQLite
- [x] Canonicalizar `related_jobs` por `related_external_id` e evitar duplicidade dentro do mesmo parent job
- [ ] Criar ingestão futura dos `related_jobs` em modo assistido

## Referências úteis

A estrutura deste projeto segue boas práticas compatíveis com a documentação oficial:
- FastAPI para request bodies tipados com Pydantic;
- Playwright com navegação controlada e locators mais resilientes;
- pytest com fixtures e parametrização para regressão com HTMLs reais.


## Observação sobre índices em `related_jobs`

Esta versão adiciona índices para otimizar consultas de vagas relacionadas em:
- `parent_job_id`
- `related_url`
- `(parent_job_id, related_url)`

> Se você já tem um `data/jobscout.db` criado antes desta versão e quiser refletir os índices e eventuais ajustes estruturais, o caminho mais simples nesta fase do projeto é recriar o banco local.
