# JobScout v2.2 (Agentic AI + CRM Integration)

Pipeline profissional para ingestão de vagas do LinkedIn e enriquecimento inteligente de dados via Groq (Llama 3.3), focado em engenharia de software pragmática e transição de carreira para Applied AI.

## 🚀 Status do Projeto: Funcional & Inteligente
- **Ingestão & Blocklist:** Extração bruta via Playwright com bloqueio automático e deduplicado por título indesejado.
- **Filtros Avançados:** Busca otimizada via SQLAlchemy (`EnrichmentFilters`) por palavras-chave, datas e campos nulos antes de acionar a IA.
- **Enriquecimento IA:** Integração com Groq LLM para cálculo de `fit_score`, extração de `skills` e análise de `english_level`.
- **Módulo de CRM:** Endpoint dedicado para gerenciar candidaturas, isolando o registro de `applied_at`, notas de entrevistas (`notes`) e pretensão salarial (`salary_expectation`).
- **Qualidade:** 128 testes unitários e de integração aprovados.

---

## 📋 Checklist / Roadmap

### ✅ Concluído (Fases 1 e 2)
- [x] Ingestão de vagas via URL e extração de DOM.
- [x] Implementação da Blocklist (Porteiro) na ingestão e no enriquecimento.
- [x] Correção de duplicação na tabela `blocked_jobs`.
- [x] Integração base com Groq LLM para calcular `fit_score` e preencher `english_level`.
- [x] Implementação de Filtros Avançados (datas, keywords no título, flags de nulos).
- [x] **Fluxo de Candidatura (CRM):** Endpoint implementado para marcar vaga como aplicada (`applied_at`).
- [x] **Gestão de Notas (CRM):** Funcionalidade para edição dos campos `notes` e `salary_expectation`.

### ⏳ Pendente (Fase 3 - Atual)
- [ ] **Refinamento de Pesos (Prompt):** Ajustar o prompt da Groq para aplicar pesos numéricos específicos no `fit_score` (ex: +pontos para FastAPI, -pontos para tecnologias indesejadas).
- [ ] **Automação (Background Tasks):** Criar um worker para processar o enriquecimento de IA automaticamente logo após a ingestão.
- [ ] **Migrações de Banco (Alembic):** Substituir o script manual `migrate_db.py` por migrações formais para facilitar a evolução do esquema.

---

## 🛠️ Stack Tecnológica
- **Backend:** FastAPI & Pydantic v2.
- **IA:** Groq Cloud (Llama-3.3-70b-versatile).
- **Crawler:** Playwright.
- **ORM/DB:** SQLAlchemy 2.x & SQLite.
- **Logging:** Structlog.

---

## ⚙️ Configuração (IA & IA Agent)

Certifique-se de configurar o seu perfil e as chaves no arquivo `.env`:

```env
# Configurações da Groq (IA)
GROQ_API_KEY="gsk_..."
GROQ_MODEL="llama-3.3-70b-versatile"

# Contexto para o Agente de IA
USER_PROFILE_CONTEXT="Backend Software Engineer (Python Pleno) em transição para Applied AI Engineering..."

# Filtro de Títulos
JOB_TITLE_BLOCKLIST="mkt,marketing,vendas,frontend"

Pipeline profissional para ingestão de vagas do LinkedIn por URL direta e promoção de vagas relacionadas, focado em observabilidade e qualidade de dados.

## Principais Funcionalidades
- HTML bruto salvo em disco para auditoria.
- Payload com campos opcionais de confirmação (`title`, `company`, `location_raw`, `is_easy_apply`, `seniority_hint`, `workplace_type`).
- Extração da vaga principal + captura de **Mais vagas** em tabela separada (`related_jobs`).
- Status técnico da coleta separado do status funcional da vaga.
- **[NOVO] Filtro "Porteiro" (Blocklist):** Rejeição automática de vagas pelo título (ex: Vendas, Marketing) sem poluir a base principal.
- **[NOVO] Observabilidade de Bloqueios:** Vagas barradas pelo filtro são registradas na tabela `blocked_jobs` contendo a URL e o motivo do bloqueio.
- **[NOVO] Campos IA/CRM:** A tabela `jobs` está preparada (`nullable=True`) para receber integrações futuras de LLMs, incluindo `skills`, `fit_score`, `fit_rationale`, `salary_raw` e `applied_at`.

> **Uso responsável:** o LinkedIn restringe scraping automatizado em seus termos e em seu `robots.txt`. Use este projeto apenas em contextos autorizados, pessoais ou de pesquisa, com volume baixo e uma URL por vez.

---

## O que esta versão resolve e corrige

Esta versão incorpora ajustes observados nos HTMLs reais e melhorias de arquitetura:

- Configuração de `blocklist` via `.env` (ex: `JOB_TITLE_BLOCKLIST="mkt,marketing,vendas"`).
- O endpoint de promoção em lote agora detecta vagas bloqueadas pela blocklist e marca a `RelatedJob` como `blocked`, documentando o erro na coluna `last_promotion_error`.
- Limpeza de `location_raw` para remover ruído como `há 1 dia`, `Mais de 100 candidaturas`, `25 pessoas clicaram em Candidate-se`.
- Limpeza de `title` quando vier poluído pelo fallback da aba (`| Empresa`, `(Remoto)`, `| LinkedIn`).
- Detecção de `workplace_type` a partir do topo **e** da descrição da vaga.
- Detecção de vaga fechada por texto como `Não aceita mais candidaturas`.
- Separação entre:
  - `status` = resultado técnico da extração;
  - `availability_status` = situação funcional da vaga.
- Captura de cards de **Mais vagas** em `related_jobs`, com `canonical_related_job_url` único garantido por UniqueConstraint global.

---

## Como rodar a API

1. Ative o seu ambiente virtual (ex: `conda activate job_scout`).
2. Crie ou atualize o seu arquivo `.env` na raiz do projeto com as suas configurações e palavras proibidas:
   ```env
   JOB_TITLE_BLOCKLIST="mkt,marketing,vendas,sales,representante,sdr,bdr"

3. Execute o script de inicialização:

PowerShell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\start_api.ps1

4. A documentação interativa (Swagger) estará disponível em: http://localhost:8000/docs

Como rodar os scripts de ingestão
Você pode processar um arquivo de texto contendo URLs usando o script PowerShell incluído.

Crie um arquivo .txt com uma URL por linha (ex: jobs_to_process.txt) e rode:

PowerShell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\process_urls.ps1 -InputFile "jobs_to_process.txt"
Como extrair vagas do banco
Para exportar os dados do banco para uma planilha Excel:

PowerShell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\export_jobs_to_excel.ps1
(Os arquivos serão salvos na pasta logs/ com a data e hora da exportação).

Como visualizar o banco local
Recomendamos o uso do DBeaver ou do DB Browser for SQLite.
Abra o arquivo localizado em data/jobscout.db.

Você encontrará três tabelas principais:

jobs: Vagas validadas e processadas (prontas para IA/CRM).

related_jobs: Vagas descobertas aguardando promoção.

blocked_jobs: Vagas rejeitadas pela regra da blocklist.

Como executar os testes
O projeto possui uma suíte robusta de 121 testes unitários, cobrindo extração de DOM, limpeza de texto, regras de bloqueio e integração de banco de dados.

Todos os testes:

Bash
pytest -v
No Windows, o fluxo oficial do projeto e de logs continua sendo o script:

PowerShell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\run_pytest.ps1
Observações:

se houver mudança de schema em SQLite sem Alembic, apague data/jobscout.db antes de subir a API novamente ou rode o script de migração manual.

os testes de regressão usam fixtures reais de HTML do LinkedIn já incluídas no projeto.

Observações de implementação
o serviço de promoção foi mantido com linkedin no nome porque o fluxo, os seletores e a normalização são específicos do LinkedIn;

o endpoint em lote reaproveita o mesmo pipeline interno de ingestão da vaga principal, evitando duplicação de regra de negócio, garantindo que a blocklist funcione em ambos.

a API segue organizada em múltiplos arquivos FastAPI, e os testes de rota podem sobrescrever dependências via app.dependency_overrides. A documentação oficial do FastAPI descreve tanto esse padrão de override quanto o uso de TestClient para testar rotas, enquanto a documentação do SQLAlchemy 2.x cobre constraints e relacionamentos ORM.