# Architecture

## Purpose

This document describes the high-level architecture of Job Scout and explains how the main subsystems interact.

The project is intentionally split into distinct layers so that job scraping, AI enrichment, and browser-based AI automation do not become entangled.

## Architectural principles

The current structure is based on these principles:

- keep scraping concerns separate from AI-provider concerns
- isolate browser automation from domain ingestion logic
- centralize configuration and prompts
- make adapters replaceable and testable
- preserve a clear boundary between automated tests and manual operational checks

## Main layers

## 1. Source adapters for scraping

Location:

```text
src/adapters/
```

This layer is responsible for ingesting job postings from supported sources.

Core elements include:

- `src/adapters/base.py`
- `src/adapters/factory.py`
- source-specific adapters such as `src/adapters/linkedin/`

### Responsibilities

- identify which adapter should handle a given URL
- fetch remote content
- extract relevant vacancy fields
- normalize data into a consistent internal structure

### Notes

This layer should remain focused on vacancy-source ingestion. It should not directly manage browser-based AI providers such as ChatGPT or Gemini.

## 2. Browser AI provider layer

Location:

```text
src/adapters/ai_web/
```

This layer was introduced to isolate browser-driven AI automation from the scraping domain.

Expected structure:

```text
src/adapters/ai_web/
  factory.py
  base/
  chatgpt/
  gemini/
```

### Responsibilities

- provide a consistent provider selection mechanism
- encapsulate provider-specific selectors and browser behavior
- execute prompts in authenticated browser sessions
- normalize response handling for browser-based providers
- save operational logs and metadata

### Why this layer exists

Browser-based providers are operationally different from scraping adapters:

- they rely on persistent user sessions
- they depend on UI selectors
- they are subject to third-party DOM changes
- they behave more like interactive clients than like content sources

Keeping them isolated reduces coupling and makes failures easier to reason about.

## 3. Core configuration and prompt management

Location:

```text
src/core/
```

Important files:

- `config.py`
- `prompts_ai.py`

### Responsibilities

- load and expose environment-backed settings
- centralize provider URLs, timeouts, profile directories, and feature toggles
- define shared and provider-specific prompts

### Design guideline

Sensitive values and environment-specific details should live in `.env`, while parsing, defaults, and access patterns belong in `config.py`.

## 4. Application services

Location:

```text
src/services/
```

Important files include:

- `ingest_service.py`
- `ai_enrichment_service.py`
- `browser_ai_service.py`

### Responsibilities

- orchestrate use cases across adapters and helpers
- keep business/application flow out of low-level adapters
- expose higher-level operations such as ingesting a vacancy or executing a browser AI prompt

### Service separation

The main service split is:

- `ingest_service.py` for source ingestion
- `ai_enrichment_service.py` for enrichment logic
- `browser_ai_service.py` for browser-based AI interaction

This separation prevents a single service from becoming a dumping ground for unrelated logic.

## 5. Utilities and persistence

Location:

```text
src/utils/
```

Important example:

- `storage.py`

### Responsibilities

- persist logs and other operational artifacts
- provide shared file-based storage helpers
- keep low-level serialization outside services and adapters

## Execution flows

## Flow A: vacancy ingestion

1. a job URL reaches the ingestion service
2. the ingestion service asks `AdapterFactory` for a matching source adapter
3. the adapter fetches the content
4. the adapter extracts and normalizes the vacancy data
5. the normalized output is returned for downstream use

## Flow B: AI enrichment

1. normalized vacancy content is passed to the enrichment service
2. prompts and settings are loaded from the core layer
3. enrichment is performed using the configured mechanism
4. structured outputs are persisted or returned to the caller

## Flow C: browser AI execution

1. a prompt is sent to `browser_ai_service.py`
2. the service selects a provider through `src/adapters/ai_web/factory.py`
3. Playwright launches a persistent browser context using the configured profile directory
4. the provider adapter interacts with the target website
5. the provider response is captured and normalized
6. the result is logged with provider metadata

## Testing strategy

The project uses two complementary testing approaches.

### Automated tests

Automated tests live in `tests/` and cover logic that should remain stable under local CI-style execution.

Focus areas include:

- factories
- services
- prompt selection
- storage helpers
- provider-layer abstractions

### Manual operational checks

Scripts under `scripts/` are used to validate real provider behavior in the browser.

Examples:

- `scripts/manual_chatgpt_check.py`
- `scripts/manual_gemini_check.py`

These scripts are useful because browser AI providers depend on login state, page structure, and timing behavior that are difficult to model perfectly in unit tests.

## Risks and trade-offs

## Browser AI fragility

The `ai_web` layer is useful, but it has known operational risks:

- selectors can break when providers redesign pages
- login/session state can expire
- DOM timing can vary
- chat reuse can introduce context contamination

Because of that, browser AI automation should be treated as an operational integration layer, not as a core deterministic domain model.

## Provider session reuse

Persistent profiles improve usability, but they also introduce behavior that depends on the current session state. This can be beneficial operationally, but it should be handled carefully.

## Recommended direction

The architecture is in a good place when:

- scraping adapters remain separate from browser AI providers
- provider-specific UI logic stays inside `ai_web`
- services orchestrate rather than own low-level browser logic
- documentation and tests stay aligned with the implementation
