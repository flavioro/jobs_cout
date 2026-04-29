# LinkedIn Search

Este documento descreve a coleta de vagas a partir das páginas de busca do LinkedIn.

## Objetivo

Permitir que o projeto descubra várias vagas a partir de uma URL de busca do LinkedIn e, opcionalmente, grave as vagas abertas na tabela `Job`.

A feature tem dois modos principais:

1. **auditoria/coleta**: gera Excel, HTML e screenshot sem gravar no banco
2. **coleta + ingestão**: coleta as vagas e chama o pipeline de ingestão por URL para persistir na tabela `Job`

## Login persistente

Antes de coletar buscas, crie ou atualize o profile persistente do LinkedIn:

```bash
python -m scripts.login_linkedin
```

O profile padrão é configurado por:

```env
LINKEDIN_PROFILE_PATH=data/linkedin_profile
```

Esse diretório não deve ser versionado.

## Arquivo de URLs de busca

As URLs de busca ficam em:

```env
LINKEDIN_SEARCH_URLS_PATH=data/linkedin_search_urls.json
```

Exemplo conceitual:

```json
[
  "https://www.linkedin.com/jobs/search/?keywords=Desenvolvedor%20Python&location=S%C3%A3o%20Paulo%20e%20Regi%C3%A3o"
]
```

O arquivo real em `data/` não deve ser versionado quando contiver buscas pessoais.

## Modo auditoria

```bash
python -m scripts.collect_linkedin_search_jobs
```

Esse modo:

- abre as URLs de busca
- faz scroll incremental
- captura cards
- completa cards parciais
- detecta vagas expiradas
- gera Excel
- salva HTML e screenshot de debug
- não grava no banco

É o modo recomendado para validar se o LinkedIn mudou DOM ou se a busca está retornando resultados coerentes.

## Modo dry-run de ingestão

```bash
python -m scripts.collect_linkedin_search_jobs --ingest --dry-run
```

Esse modo executa a coleta e simula a ingestão, mas não grava no banco.

Use antes da primeira ingestão real.

## Modo ingestão real

```bash
python -m scripts.collect_linkedin_search_jobs --ingest
```

Esse modo:

1. coleta as vagas da busca
2. ignora vagas fechadas por padrão
3. chama o mesmo pipeline de `POST /ingest-url`
4. salva ou atualiza registros na tabela `Job`
5. exibe um resumo final

## Flags úteis

### `--ingest`

Ativa a gravação real na tabela `Job`.

### `--dry-run`

Com `--ingest`, simula a gravação sem persistir.

### `--max-jobs-per-url 10`

Limita quantas vagas serão processadas por URL de busca.

### `--stop-on-error`

Interrompe no primeiro erro de ingestão.

### `--include-closed`

Inclui vagas fechadas/expiradas no processamento. Por padrão, elas são ignoradas.

### `--no-export-xlsx`

Desabilita a exportação do Excel de auditoria.

### `--export-xlsx-path caminho.xlsx`

Define um caminho alternativo para o Excel.

## Configurações principais

```env
LINKEDIN_PROFILE_PATH=data/linkedin_profile
LINKEDIN_SEARCH_URLS_PATH=data/linkedin_search_urls.json
LINKEDIN_SEARCH_SCROLL_STEPS=8
LINKEDIN_SEARCH_SCROLL_DELAY_S=1.5
LINKEDIN_SEARCH_INITIAL_WAIT_S=2.0
LINKEDIN_SEARCH_DETAIL_WAIT_S=1.5
LINKEDIN_SEARCH_STABLE_SCROLL_ROUNDS=3
LINKEDIN_SEARCH_CARD_LIMIT_PER_URL=25
LINKEDIN_SEARCH_EXPORT_XLSX_ENABLED=true
LINKEDIN_SEARCH_EXPORT_XLSX_PATH=data/exports/linkedin_search_cards.xlsx
LINKEDIN_SEARCH_SKIP_CLOSED=true
```

## Resultado esperado

Uma execução bem-sucedida pode produzir algo como:

```text
collected_count: 25
complete_count: 24
closed_count: 1
processed: 24
success_count: 24
failed_count: 0
skipped_count: 1
```

## Deduplicação

A deduplicação acontece em dois níveis:

1. na coleta, por `linkedin_job_id` ou URL canônica
2. na ingestão, pelo pipeline existente de persistência/upsert da tabela `Job`

Após implementar ou alterar a feature, rode o modo `--ingest` duas vezes com a mesma busca para validar que não há duplicação indevida.

## Artefatos gerados

Por padrão:

- Excel: `data/exports/linkedin_search_cards.xlsx`
- HTML: `data/debug/linkedin_search_<timestamp>.html`
- Screenshot: `data/debug/linkedin_search_<timestamp>.png`

Esses arquivos são operacionais e não devem ir para o Git.

## Endpoint da API

Além do script, a API expõe endpoint para coleta/ingestão:

```text
POST /linkedin/search-jobs/collect-ingest
```

Use o script para validação local e o endpoint quando precisar integrar a automação com outro fluxo.

## Limitações conhecidas

- O LinkedIn virtualiza a lista de resultados; o total visual da busca pode ser maior que o total capturado em uma execução.
- Mudanças no DOM do LinkedIn podem exigir ajuste de seletores.
- Sessão expirada pode exigir novo `python -m scripts.login_linkedin`.
- O modo browser depende de Playwright e de uma sessão autenticada estável.

## Checklist operacional

Antes de usar em rotina:

```text
[x] Login LinkedIn feito
[x] URL de busca cadastrada
[x] Coleta simples gera Excel
[x] Dry-run de ingestão passa
[x] Ingestão real grava na tabela Job
[x] Segunda execução não duplica vagas
```
