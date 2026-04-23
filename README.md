# Job Scout

Job Scout is a Python-based project for collecting job postings, normalizing structured vacancy data, enriching results with AI, and supporting browser-based AI providers such as ChatGPT and Gemini through a dedicated `ai_web` layer.

The project separates three concerns:

- **Scraping**: adapters that ingest job postings from supported sources such as LinkedIn.
- **Enrichment**: services that transform raw vacancy content into structured, more useful outputs.
- **Browser AI automation**: a dedicated layer for interacting with web-based AI providers in a controlled and testable way.

## Overview

Job Scout was designed to make job data ingestion and post-processing easier to maintain over time. Instead of mixing scraping logic, AI logic, and browser automation in the same modules, the project now uses a clearer architecture:

- `src/adapters/` for source adapters used by the ingestion pipeline.
- `src/adapters/ai_web/` for browser-based AI providers.
- `src/services/` for orchestration and application services.
- `src/core/` for configuration and prompt management.
- `src/utils/` for shared helpers such as persistence and logging.

This separation makes it easier to add new job sources, add new AI providers, test each layer independently, and keep operational scripts out of the automated test flow.

## Quick start

### 1. Create and activate your environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install
```

### 3. Configure environment variables

Copy the example file and adjust values for your environment:

```bash
cp .env.example .env
```

Important settings usually include:

- API keys used by enrichment services
- Playwright/browser configuration
- profile directories for ChatGPT and Gemini
- provider-specific URLs and timeouts

### 4. Create persistent browser profiles

The browser-based providers rely on persistent profiles so that authenticated sessions can be reused.

Run the manual login scripts when needed:

```bash
python -m scripts.login_chatgpt
python -m scripts.login_gemini
```

### 5. Run unit tests

```bash
pytest
```

Or use the PowerShell helper on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\powershell\run_pytest.ps1
```

### 6. Run manual provider checks

```bash
python -m scripts.manual_chatgpt_check
python -m scripts.manual_gemini_check
```

These scripts are intended for operational validation and should not replace automated tests.

## Features

- modular ingestion adapters for job sources
- structured vacancy normalization
- AI enrichment pipeline for job data
- dedicated `ai_web` browser automation layer for ChatGPT and Gemini
- provider-specific prompts with shared fallback support
- persistent browser profiles for authenticated sessions
- structured response logging with provider metadata
- separated manual checks and automated tests
- documentation for architecture, scraping, enrichment, and roadmap

## High-level architecture

At a high level, the project is organized into three main flows.

### 1. Scraping flow

A job URL enters the ingestion service. The service resolves the correct source adapter through `AdapterFactory`, then uses the selected adapter to fetch, extract, and normalize vacancy data.

### 2. Enrichment flow

Normalized vacancy data can be passed into enrichment services that produce structured outputs, summaries, classifications, or other useful metadata.

### 3. Browser AI flow

When web-based AI interaction is required, the request goes through the `ai_web` layer, which selects a provider such as ChatGPT or Gemini and runs the prompt through Playwright using a persistent browser profile.

## Repository structure

```text
src/
  adapters/
    base.py
    factory.py
    linkedin/
    ai_web/
      factory.py
      base/
      chatgpt/
      gemini/
  core/
    config.py
    prompts_ai.py
  services/
    ingest_service.py
    ai_enrichment_service.py
    browser_ai_service.py
  utils/
    storage.py

scripts/
  login_chatgpt.py
  login_gemini.py
  manual_chatgpt_check.py
  manual_gemini_check.py
  powershell/

docs/
  architecture.md
  enrichment.md
  scraping.md
  roadmap.md
```

## Testing

The project distinguishes between automated tests and manual provider checks.

### Automated tests

Automated tests live under `tests/` and are the default target for `pytest`. The repository includes unit coverage for the newer `ai_web` layer and supporting services.

### Manual checks

Manual checks are executed through scripts in `scripts/` and are useful when validating:

- persistent browser profiles
- provider login state
- selector stability
- real-world behavior in ChatGPT or Gemini

## Operational notes

Browser-based AI providers are inherently more fragile than API integrations because they depend on:

- page structure and selectors
- authenticated sessions
- browser timing
- UI changes made by third-party providers

Because of that, the project treats these integrations as a dedicated operational layer rather than mixing them into the core scraping domain.

## Documentation

Detailed documentation is available in:

- `docs/architecture.md`
- `docs/enrichment.md`
- `docs/scraping.md`
- `docs/roadmap.md`

## Current status

The current architecture already includes:

- Gemini support through the browser automation layer
- ChatGPT and Gemini organized under the same `ai_web` structure
- separation between scraping adapters and browser AI providers
- automated tests plus manual validation scripts

The next natural step is to keep the documentation aligned with the implementation and continue improving operational robustness where needed.
