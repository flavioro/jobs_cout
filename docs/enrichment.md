# Enrichment

## Purpose

This document explains how Job Scout enriches vacancy data and where browser-based AI providers fit into that process.

The key idea is that enrichment is not the same as scraping.

- **Scraping** collects and normalizes raw vacancy information.
- **Enrichment** adds interpretation, structure, summarization, categorization, or additional metadata.

## Enrichment goals

Typical enrichment goals include:

- classify the vacancy by sector or area
- estimate seniority level
- identify primary technologies or keywords
- generate summaries
- structure semi-free-text descriptions into consistent fields

## Inputs and outputs

### Input

A normalized vacancy object or a vacancy description obtained from the scraping layer.

### Output

A more structured representation that may include fields such as:

- sector
- seniority
- technologies
- summary
- additional analytical metadata

## Main components

### `src/services/ai_enrichment_service.py`

This service should orchestrate enrichment use cases.

Its responsibilities typically include:

- receiving normalized vacancy content
- selecting the appropriate prompt or enrichment flow
- calling the configured enrichment mechanism
- handling the structured result

### `src/core/prompts_ai.py`

This module centralizes prompts used by AI-related flows.

It supports two categories of prompts:

- **shared prompts**, used across providers
- **provider-specific prompts**, used when a provider needs different wording or validation behavior

This avoids scattering prompt text across scripts and adapters.

## Where browser AI fits

Browser-based AI providers such as ChatGPT and Gemini should not be treated as scraping adapters.

Instead, they fit as optional enrichment or operational analysis tools through the `ai_web` layer.

### Why this matters

If browser providers are mixed directly into the scraping layer, the codebase becomes harder to reason about because these responsibilities are fundamentally different:

- scraping retrieves content from job sources
- browser AI providers interpret content through an interactive third-party UI

## Prompt strategy

A good prompt strategy in this project should follow these rules:

- keep prompts centralized
- prefer shared prompts when provider-specific wording is unnecessary
- use provider-specific prompts only when there is a clear operational need
- avoid embedding large prompt strings directly inside scripts or adapters

## Example enrichment prompt shape

A typical enrichment flow may ask for a JSON-like structured response containing fields such as:

- primary sector
- seniority
- top technologies
- summary

When using formatted prompt templates, be careful with literal braces in JSON examples so that string formatting does not interpret them as placeholders.

## Persistence and logging

Enrichment-related operations should leave enough information behind for debugging and auditing.

At minimum, useful metadata may include:

- provider used
- prompt name
- response text
- chat URL when applicable
- selector or execution metadata for browser AI

## Design recommendation

Keep enrichment orchestration in services and keep provider-specific browser interaction inside the `ai_web` adapters.

A healthy structure looks like this:

- `ai_enrichment_service.py` decides *what* enrichment should happen
- `browser_ai_service.py` decides *which browser provider* to use for that prompt
- provider adapters decide *how* to interact with each provider's web UI

## Risks

### 1. Context contamination in reused chats

If enrichment uses an existing chat instead of starting fresh, previous conversation history can affect the result.

### 2. Provider output variability

Even with the same prompt, browser-based providers may vary in wording or formatting.

### 3. UI dependence

Unlike API-based enrichment, browser AI depends on selectors, session state, and timing.

## Good practices

- prefer isolated prompts for repeatable enrichment tasks
- log provider metadata for debugging
- separate enrichment orchestration from browser automation details
- keep test prompts minimal and deterministic where possible
