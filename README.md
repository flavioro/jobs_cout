# Job Scout

Job Scout é um pipeline para ingestão de vagas do LinkedIn, enriquecimento por IA e automação opcional de provedores web como ChatGPT e Gemini.

## Visão geral

O projeto combina três frentes:

- scraping resiliente de vagas do LinkedIn via Playwright
- enriquecimento estruturado por LLM para fit, skills, inglês e setor
- automação web opcional para provedores conversacionais com perfil persistente

## Quick start

1. Crie e ative seu ambiente virtual.
2. Instale dependências com `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` e ajuste as variáveis.
4. Rode a API com `uvicorn src.main:app --reload`.
5. Rode os testes com `pytest` ou com o script PowerShell do projeto.

## Features

- ingestão de vagas por URL do LinkedIn
- normalização, deduplicação e blocklist por título
- persistência em SQLite com SQLAlchemy assíncrono
- enriquecimento por Groq
- automação web para ChatGPT e Gemini com chat novo ou chat existente por URL
- logging de respostas de browser AI em JSON lines

## Arquitetura

Em alto nível, o projeto é dividido em:

- `src/adapters/linkedin`: coleta e extração de vagas
- `src/services`: orquestração de ingestão, persistência e enrichment
- `src/adapters/ai_web`: automação web de provedores de IA
- `src/api`: endpoints FastAPI
- `src/db`: modelos e sessão do banco

Mais detalhes estão em `docs/architecture.md`.

## Documentação detalhada

- `docs/architecture.md`
- `docs/enrichment.md`
- `docs/scraping.md`
- `docs/roadmap.md`

## Testes

- unitários e integração: `pytest`
- smoke manual para providers: `python scripts/test_chatgpt.py` e `python scripts/test_gemini.py`

## Observação sobre browser AI

O modo padrão é `new_chat`, mais previsível para automação. O modo `existing_chat` é suportado via URL configurável, mas traz risco maior de contaminação de contexto.
