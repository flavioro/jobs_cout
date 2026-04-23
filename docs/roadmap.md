# Roadmap

## Purpose

This document tracks the current direction of Job Scout after the introduction of the `ai_web` layer and Gemini support.

It focuses on realistic next steps rather than speculative long-term ideas.

## Recently completed

The following work has already been delivered in the current architecture direction:

- added browser-based Gemini support
- organized ChatGPT and Gemini under a dedicated `src/adapters/ai_web/` layer
- removed legacy browser provider adapters from the older adapter layout
- separated manual provider scripts from automated tests
- improved prompt centralization through `src/core/prompts_ai.py`
- introduced `browser_ai_service.py`
- cleaned up the architecture so scraping and browser AI are no longer mixed
- added or reorganized documentation and tests around the new structure

## Current focus

The current focus is documentation polish and architectural clarity.

Priority items:

- keep README concise and professional
- ensure docs reflect the actual repository structure
- document the separation between scraping, enrichment, and browser AI
- keep tests aligned with the new architecture

## Near-term priorities

### 1. Operational robustness for browser AI

Continue improving the `ai_web` layer with a focus on:

- more resilient selector strategies
- better response extraction and cleanup
- clearer retry behavior
- more explicit metadata in logs

### 2. Test coverage improvements

Expand automated coverage for:

- provider factory behavior
- prompt resolution
- response logging
- retry scenarios
- `new_chat` versus `existing_chat` behavior where applicable

### 3. Documentation quality

Continue refining:

- README examples
- architecture docs
- provider operation notes
- test execution instructions

## Medium-term opportunities

### 1. Better provider observability

Potential improvements:

- elapsed-time metrics
- clearer retry counts
- selector provenance in logs
- easier debugging artifacts for browser flows

### 2. Provider-mode control

Support and document configurable browser AI modes such as:

- always start a new chat
- reuse an existing chat by URL

This should remain optional and be treated carefully because reused chats can introduce hidden context.

### 3. Additional provider support

The `ai_web` architecture makes it easier to evaluate future providers if needed.

This should only be done when:

- there is a clear use case
- the provider can be isolated cleanly
- the operational cost is justified

## What should remain stable

The following architectural boundaries should remain intact:

- scraping adapters are for job sources
- browser AI providers are for interactive AI websites
- services orchestrate use cases
- prompts remain centralized
- manual checks remain separate from automated tests

## Suggested next backlog after docs

Once the documentation pass is complete, the next practical backlog could be:

1. strengthen provider selector fallbacks
2. improve response extraction consistency
3. validate structured logging schema with tests
4. improve retry strategy and diagnostics
5. expand smoke test documentation

## Non-goals for now

These items are not current priorities:

- merging scraping and browser AI factories
- hiding all provider-specific behavior behind one large generic class
- treating browser AI providers as deterministic API clients

## Summary

The project is now in a healthier architectural state than before the Gemini work started.

The next phase is not about adding more layers; it is about consolidating the quality of what already exists:

- clearer docs
- stronger operational robustness
- more predictable tests
- continued architectural discipline
