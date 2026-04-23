# Scraping

## Purpose

This document describes the scraping layer of Job Scout and how source-specific adapters are expected to behave.

The scraping layer is responsible for turning an external job posting source into normalized data that can later be enriched or persisted.

## Scope

This document covers the classic source adapter flow, not the browser AI provider layer.

Relevant modules are generally found under:

```text
src/adapters/
```

with examples such as:

- `src/adapters/base.py`
- `src/adapters/factory.py`
- `src/adapters/linkedin/`

## Responsibilities of the scraping layer

- accept a source URL
- select the correct adapter for that source
- fetch the remote content
- extract relevant vacancy fields
- normalize the output shape

## Base contract

### `src/adapters/base.py`

The base adapter should define the common contract expected from source adapters.

Typical responsibilities of a base contract:

- establish required methods
- standardize adapter behavior
- make orchestration simpler for services such as `ingest_service.py`

## Adapter resolution

### `src/adapters/factory.py`

The factory is responsible for mapping a source URL to the correct adapter implementation.

For example, if the URL belongs to LinkedIn, the factory returns the LinkedIn adapter.

This logic belongs to the scraping domain and should remain independent from browser AI provider selection.

## LinkedIn adapter example

The LinkedIn adapter is an example of a concrete source adapter.

Its internal responsibilities may include:

- downloading or receiving the page content
- selecting fields from the page structure
- extracting job title, company, description, location, and related data
- normalizing the result into the project's expected schema

### Supporting modules

A source adapter may rely on helper modules such as:

- selectors
- extractor logic
- normalization helpers

These should remain scoped to the source adapter rather than leaking into unrelated layers.

## Ingestion flow

A typical ingestion flow looks like this:

1. the application receives a vacancy URL
2. `ingest_service.py` calls `AdapterFactory`
3. the selected adapter fetches and parses the content
4. the adapter returns a normalized vacancy structure
5. downstream services may persist or enrich that structure

## Separation from `ai_web`

It is important to keep scraping and browser AI separate.

### Scraping adapters

- represent external job sources
- are selected based on vacancy URLs
- focus on content extraction and normalization

### Browser AI providers

- represent conversational tools such as ChatGPT and Gemini
- are selected based on provider name, not vacancy URL
- focus on browser automation and prompt execution

Mixing these two responsibilities leads to confusing factories and harder-to-maintain services.

## Testing recommendations

For the scraping layer, useful tests generally include:

- factory selection tests
- extraction tests using saved content or fixtures
- normalization tests
- integration tests around the ingestion service

## Operational recommendations

- keep selectors and extractor logic close to the source adapter
- avoid putting provider-specific browser AI code in the scraping tree
- prefer deterministic parsing where possible
- log enough information to debug extraction failures
