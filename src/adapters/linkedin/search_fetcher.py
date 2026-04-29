from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright
from src.adapters.linkedin.extractor import LinkedInExtractor
from src.core.contracts import RawPage

from src.core.config import get_settings

_CARD_SELECTOR = "li[data-occludable-job-id], div.job-card-container[data-job-id], li.scaffold-layout__list-item"
_LIST_SELECTOR = ".jobs-search-results-list, .scaffold-layout__list-container, ul.scaffold-layout__list-container"

_CLOSED_MARKERS_JS = [
    "expirado",
    "vaga expirada",
    "candidaturas encerradas",
    "candidatura encerrada",
    "não aceita mais candidaturas",
    "nao aceita mais candidaturas",
    "não está mais aceitando candidaturas",
    "nao esta mais aceitando candidaturas",
    "não recebe mais candidaturas",
    "nao recebe mais candidaturas",
    "no longer accepting applications",
    "job expired",
    "applications are closed",
]


class LinkedInSearchSession:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._playwright = None
        self.context = None
        self.page = None
        self.last_debug_html_path: str | None = None
        self.last_debug_screenshot_path: str | None = None
        self.last_scroll_metadata: dict[str, Any] = {}

    async def __aenter__(self) -> "LinkedInSearchSession":
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def open(self) -> None:
        if self.page is not None:
            return
        profile_dir = Path(self.settings.linkedin_profile_path)
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self.context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=self.settings.playwright_headless,
            viewport={"width": 1440, "height": 960},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page.set_default_timeout(self.settings.playwright_timeout_ms)

    async def close(self) -> None:
        if self.context is not None:
            await self.context.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self.context = None
        self.page = None
        self._playwright = None

    async def fetch_search_page(self, url: str) -> str:
        await self._open_search(url)
        await self._scroll_collecting_cards(url, complete_partials=False)
        assert self.page is not None
        html = await self.page.content()
        await self._save_debug_artifacts(url, html)
        return html

    async def fetch_search_cards(self, url: str) -> list[dict[str, Any]]:
        """Collect cards from a LinkedIn search page.

        The collector extracts cards incrementally while scrolling the left
        results pane. This is important because LinkedIn virtualizes the list:
        cards that were visible can leave the DOM after the next scroll. Any
        link-only/partial result is preserved and later completed by opening the
        individual job URL.
        """
        await self._open_search(url)
        raw_cards = await self._scroll_collecting_cards(url, complete_partials=True)
        assert self.page is not None
        html = await self.page.content()
        await self._save_debug_artifacts(url, html)
        return raw_cards

    async def _open_search(self, url: str) -> None:
        if self.page is None:
            await self.open()
        assert self.page is not None
        await self.page.goto(url, wait_until="domcontentloaded", timeout=self.settings.playwright_timeout_ms)
        await self.page.wait_for_timeout(int(self.settings.linkedin_search_initial_wait_s * 1000))
        await self._wait_for_cards()

    async def _wait_for_cards(self) -> None:
        assert self.page is not None
        try:
            await self.page.locator(_CARD_SELECTOR).first.wait_for(state="attached", timeout=8000)
        except Exception:
            pass

    async def _card_count(self) -> int:
        assert self.page is not None
        try:
            return await self.page.locator(_CARD_SELECTOR).count()
        except Exception:
            return 0

    async def _scroll_collecting_cards(self, url: str, *, complete_partials: bool) -> list[dict[str, Any]]:
        """Scroll the results pane and collect cards after every movement.

        We deduplicate incrementally because LinkedIn can remove cards from the
        DOM while new cards are loaded. A later, richer observation of the same
        job replaces an earlier link-only observation.
        """
        max_steps = max(0, int(self.settings.linkedin_search_scroll_steps))
        pause_s = max(0.2, float(self.settings.linkedin_search_scroll_delay_s))
        stable_limit = max(1, int(self.settings.linkedin_search_stable_scroll_rounds))
        seen: dict[str, dict[str, Any]] = {}
        stable_rounds = 0
        steps_done = 0
        before_count = await self._card_count()
        last_seen_count = 0
        last_scroll_top = -1
        last_scroll_height = -1

        # Capture the first viewport before any scrolling.
        self._merge_cards_into_seen(seen, await self._extract_visible_cards())
        last_seen_count = len(seen)

        for step in range(max_steps):
            steps_done = step + 1
            scroll_state = await self._scroll_jobs_list()
            await asyncio.sleep(pause_s)
            self._merge_cards_into_seen(seen, await self._extract_visible_cards())

            seen_count = len(seen)
            scroll_top = int(scroll_state.get("scrollTop") or 0) if isinstance(scroll_state, dict) else 0
            scroll_height = int(scroll_state.get("scrollHeight") or 0) if isinstance(scroll_state, dict) else 0
            cannot_scroll_further = bool(scroll_state.get("atBottom")) if isinstance(scroll_state, dict) else False

            no_new_cards = seen_count <= last_seen_count
            no_scroll_progress = scroll_top == last_scroll_top and scroll_height == last_scroll_height
            if no_new_cards and (cannot_scroll_further or no_scroll_progress):
                stable_rounds += 1
            elif no_new_cards:
                stable_rounds += 1
            else:
                stable_rounds = 0

            last_seen_count = seen_count
            last_scroll_top = scroll_top
            last_scroll_height = scroll_height
            if stable_rounds >= stable_limit:
                break

        raw_cards = list(seen.values())
        if complete_partials:
            completed: list[dict[str, Any]] = []
            for card in raw_cards:
                job_url = card.get("linkedin_job_url")
                if job_url and self._should_complete_from_job_url(card):
                    detail = await self._try_complete_from_job_url(job_url)
                    card = self._merge_detail(card, detail)
                card["source_search_url"] = url
                card["collected_at"] = datetime.now(timezone.utc).isoformat()
                completed.append(card)
            raw_cards = completed

        self.last_scroll_metadata = {
            "cards_before_scroll": before_count,
            "unique_cards_collected": len(raw_cards),
            "cards_after_scroll": await self._card_count(),
            "scroll_steps": steps_done,
            "stable_rounds": stable_rounds,
        }
        return raw_cards

    def _merge_cards_into_seen(self, seen: dict[str, dict[str, Any]], cards: list[dict[str, Any]]) -> None:
        for card in cards:
            key = self._card_key(card)
            if not key:
                continue
            existing = seen.get(key)
            if existing is None:
                seen[key] = dict(card)
            else:
                seen[key] = self._prefer_richer_card(existing, card)

    def _card_key(self, card: dict[str, Any]) -> str | None:
        job_id = card.get("linkedin_job_id")
        if job_id:
            return f"id:{job_id}"
        url = card.get("linkedin_job_url")
        if url:
            return f"url:{url}"
        return None

    def _card_quality_score(self, card: dict[str, Any]) -> int:
        score = 0
        for key in ("title", "company", "location_raw"):
            if card.get(key):
                score += 3
        if card.get("card_text_raw"):
            score += 1
        if card.get("availability_status") == "closed":
            score += 2
        return score

    def _prefer_richer_card(self, existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        if self._card_quality_score(incoming) > self._card_quality_score(existing):
            merged = dict(existing)
            for key, value in incoming.items():
                if value not in (None, "", []):
                    merged[key] = value
            return merged
        merged = dict(existing)
        for key, value in incoming.items():
            if merged.get(key) in (None, "", []) and value not in (None, "", []):
                merged[key] = value
        if incoming.get("availability_status") == "closed":
            merged["availability_status"] = "closed"
            merged["availability_reason"] = incoming.get("availability_reason")
        return merged

    async def _scroll_jobs_list(self) -> dict[str, Any]:
        assert self.page is not None
        state = await self.page.evaluate(
            r"""
            ({cardSelector, listSelector}) => {
              const selectors = [
                '.scaffold-layout__list',
                '.jobs-search-results-list',
                '.jobs-search-results-list__list',
                '.scaffold-layout__list-container',
                'ul.scaffold-layout__list-container',
                listSelector
              ];

              const isScrollable = (el) => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                return el.scrollHeight > el.clientHeight + 20 && /(auto|scroll|overlay)/i.test(style.overflowY || '');
              };

              let container = null;
              const firstCard = document.querySelector(cardSelector);
              let cursor = firstCard;
              while (cursor && cursor !== document.body) {
                if (isScrollable(cursor)) {
                  container = cursor;
                  break;
                }
                cursor = cursor.parentElement;
              }

              if (!container) {
                for (const selector of selectors) {
                  const candidates = Array.from(document.querySelectorAll(selector));
                  container = candidates.find(isScrollable);
                  if (container) break;
                }
              }

              if (container) {
                const before = container.scrollTop;
                const delta = Math.max(container.clientHeight * 0.82, 560);
                container.scrollTop = Math.min(container.scrollTop + delta, container.scrollHeight);
                container.dispatchEvent(new Event('scroll', { bubbles: true }));
                const atBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 8;
                return {
                  target: 'container',
                  scrolled: container.scrollTop !== before,
                  scrollTop: container.scrollTop,
                  scrollHeight: container.scrollHeight,
                  clientHeight: container.clientHeight,
                  atBottom
                };
              }

              const before = window.scrollY;
              window.scrollBy(0, Math.max(window.innerHeight * 0.82, 560));
              const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 8;
              return {
                target: 'window',
                scrolled: window.scrollY !== before,
                scrollTop: window.scrollY,
                scrollHeight: document.documentElement.scrollHeight,
                clientHeight: window.innerHeight,
                atBottom
              };
            }
            """,
            {"cardSelector": _CARD_SELECTOR, "listSelector": _LIST_SELECTOR},
        )
        if not isinstance(state, dict) or not state.get("scrolled"):
            await self.page.mouse.wheel(0, 1200)
        return state if isinstance(state, dict) else {}

    async def _extract_visible_cards(self) -> list[dict[str, Any]]:
        assert self.page is not None
        return await self.page.evaluate(
            r"""
            ({cardSelector, closedMarkers}) => {
              const clean = (value) => (value || '').replace(/\s+/g, ' ').trim() || null;
              const normalizeJobUrl = (href, jobId) => {
                if (!jobId && href) {
                  const viewMatch = href.match(/\/jobs\/view\/(\d+)/);
                  const currentMatch = href.match(/[?&]currentJobId=(\d+)/);
                  jobId = viewMatch ? viewMatch[1] : (currentMatch ? currentMatch[1] : null);
                }
                if (!jobId) return href || null;
                return `https://www.linkedin.com/jobs/view/${jobId}/`;
              };
              const jobIdFromHref = (href) => {
                if (!href) return null;
                const viewMatch = href.match(/\/jobs\/view\/(\d+)/);
                if (viewMatch) return viewMatch[1];
                const currentMatch = href.match(/[?&]currentJobId=(\d+)/);
                return currentMatch ? currentMatch[1] : null;
              };
              const closedFromText = (text) => {
                const lower = (text || '').toLowerCase();
                return closedMarkers.some(marker => lower.includes(marker));
              };
              const extractFromNode = (node, index) => {
                const link = node.querySelector("a.job-card-list__title--link, a.job-card-container__link, a[href*='/jobs/view/'], a[href*='currentJobId=']");
                const href = link ? link.href : null;
                const jobId = clean(node.getAttribute('data-occludable-job-id') || node.getAttribute('data-job-id')) || jobIdFromHref(href);
                const strong = link ? link.querySelector('strong') : null;
                let title = clean(strong ? strong.innerText : null) || clean(link ? (link.getAttribute('aria-label') || link.innerText) : null);
                if (title) title = title.replace(/\s+with verification$/i, '').trim();
                const companyNode = node.querySelector('.artdeco-entity-lockup__subtitle span, .job-card-container__primary-description');
                const locationNode = node.querySelector('.job-card-container__metadata-wrapper li span, .artdeco-entity-lockup__caption li span, .job-card-container__metadata-item');
                const cardTextRaw = clean(node.innerText) || '';
                const isClosed = closedFromText(cardTextRaw);
                const isEasyApply = /candidatura simplificada|easy apply|candidate-se facilmente/i.test(cardTextRaw) ? true : null;
                return {
                  index,
                  linkedin_job_id: jobId,
                  linkedin_job_url: normalizeJobUrl(href, jobId),
                  title,
                  company: clean(companyNode ? companyNode.innerText : null),
                  location_raw: clean(locationNode ? locationNode.innerText : null),
                  card_text_raw: cardTextRaw,
                  text: cardTextRaw,
                  is_easy_apply: isEasyApply,
                  availability_status: isClosed ? 'closed' : 'unknown',
                  availability_reason: isClosed ? 'expired_or_no_longer_accepting_applications' : null,
                  detail_completed: false,
                  detail_url_opened: false
                };
              };

              const cards = [];
              const seenKeys = new Set();
              Array.from(document.querySelectorAll(cardSelector)).forEach((node, index) => {
                const item = extractFromNode(node, index);
                const key = item.linkedin_job_id || item.linkedin_job_url;
                if (key && !seenKeys.has(key)) {
                  seenKeys.add(key);
                  cards.push(item);
                }
              });

              // Preserve link-only results too. They can be completed by opening
              // the individual job URL after the scroll loop.
              Array.from(document.querySelectorAll("a[href*='/jobs/view/'], a[href*='currentJobId=']")).forEach((link, index) => {
                const href = link.href;
                const jobId = jobIdFromHref(href);
                const normalizedUrl = normalizeJobUrl(href, jobId);
                const key = jobId || normalizedUrl;
                if (!key || seenKeys.has(key)) return;
                const text = clean(link.innerText || link.getAttribute('aria-label')) || '';
                cards.push({
                  index: 10000 + index,
                  linkedin_job_id: jobId,
                  linkedin_job_url: normalizedUrl,
                  title: text || null,
                  company: null,
                  location_raw: null,
                  card_text_raw: text,
                  text,
                  is_easy_apply: null,
                  availability_status: closedFromText(text) ? 'closed' : 'unknown',
                  availability_reason: closedFromText(text) ? 'expired_or_no_longer_accepting_applications' : null,
                  detail_completed: false,
                  detail_url_opened: false
                });
                seenKeys.add(key);
              });

              return cards.filter(item => item.linkedin_job_id || item.linkedin_job_url);
            }
            """,
            {"cardSelector": _CARD_SELECTOR, "closedMarkers": _CLOSED_MARKERS_JS},
        )

    async def _try_complete_from_job_url(self, job_url: str) -> dict[str, Any]:
        """Complete a partial search card by reusing the mature ingest-url extractor.

        The search page is only responsible for discovering job URLs. When a
        card is incomplete, this method opens the individual job URL and parses
        the resulting page with ``LinkedInExtractor``, the same extraction logic
        used by POST /ingest-url. A small DOM snapshot is still collected for
        audit/debug columns in the Excel export.
        """
        if self.context is None:
            return {}
        detail_page = await self.context.new_page()
        detail_page.set_default_timeout(self.settings.playwright_timeout_ms)
        try:
            await detail_page.goto(job_url, wait_until="domcontentloaded", timeout=self.settings.playwright_timeout_ms)
            await detail_page.wait_for_timeout(int(self.settings.linkedin_search_detail_wait_s * 1000))
            try:
                await detail_page.locator(".jobs-unified-top-card, .job-details-jobs-unified-top-card, h1").first.wait_for(
                    state="attached",
                    timeout=5000,
                )
            except Exception:
                pass

            dom_detail = await self._extract_detail_dom_snapshot(detail_page)
            html = await detail_page.content()
            page_title = await detail_page.title()
            extractor_detail = self._extract_detail_with_ingest_extractor(
                job_url=job_url,
                final_url=detail_page.url,
                html=html,
                page_title=page_title,
                detail_text=dom_detail.get("detail_text"),
            )
            return self._prefer_ingest_extractor_detail(dom_detail, extractor_detail)
        except Exception as exc:
            return {"detail_completed": False, "detail_url_opened": True, "detail_error": str(exc)}
        finally:
            await detail_page.close()

    async def _extract_detail_dom_snapshot(self, detail_page) -> dict[str, Any]:
        return await detail_page.evaluate(
            r"""
            (closedMarkers) => {
              const clean = (value) => (value || '').replace(/\s+/g, ' ').trim() || null;
              const root =
                document.querySelector('.job-view-layout, .jobs-details, .jobs-search__job-details, main') ||
                document.body;

              const titleNode = root.querySelector(
                '.job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title, h1'
              );
              const companyNode = root.querySelector(
                '.job-details-jobs-unified-top-card__company-name a, .jobs-unified-top-card__company-name a, ' +
                '.job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name'
              );
              const primaryNode = root.querySelector(
                '.job-details-jobs-unified-top-card__primary-description-container, .jobs-unified-top-card__primary-description'
              );
              const locationNode = root.querySelector(
                '.job-details-jobs-unified-top-card__primary-description-container span, ' +
                '.jobs-unified-top-card__primary-description span, .jobs-unified-top-card__bullet'
              );

              const primaryText = clean(primaryNode ? primaryNode.innerText : null);
              const explicitLocation = clean(locationNode ? locationNode.innerText : null);
              let location = explicitLocation;
              if (!location && primaryText) {
                location = clean(primaryText.split('·')[0].split(' há ')[0].split(' hÃ¡ ')[0]);
              }

              const detailText = clean(root.innerText) || '';
              const lower = detailText.toLowerCase();
              const isClosed = closedMarkers.some(marker => lower.includes(marker));
              const workplaceMatch = detailText.match(/\b(Remoto|Híbrido|Hibrido|Presencial|Remote|Hybrid|On-site|Onsite)\b/i);
              const typeMatch = detailText.match(/\b(Tempo integral|Meio período|Contrato|Full-time|Part-time|Contract)\b/i);
              const easyApply = /candidatura simplificada|easy apply|candidate-se facilmente/i.test(detailText) ? true : null;

              return {
                title: clean(titleNode ? titleNode.innerText : null),
                company: clean(companyNode ? companyNode.innerText : null),
                location_raw: location,
                detail_text: detailText,
                workplace_type_raw: workplaceMatch ? workplaceMatch[1] : null,
                employment_type_raw: typeMatch ? typeMatch[1] : null,
                is_easy_apply: easyApply,
                availability_status: isClosed ? 'closed' : 'unknown',
                availability_reason: isClosed ? 'expired_or_no_longer_accepting_applications' : null,
                detail_completed: true,
                detail_url_opened: true,
                detail_completion_source: 'dom_selectors'
              };
            }
            """,
            _CLOSED_MARKERS_JS,
        )

    def _extract_detail_with_ingest_extractor(
        self,
        *,
        job_url: str,
        final_url: str,
        html: str,
        page_title: str | None,
        detail_text: str | None = None,
    ) -> dict[str, Any]:
        try:
            payload = LinkedInExtractor().extract(
                RawPage(
                    url=job_url,
                    final_url=final_url or job_url,
                    html=html,
                    title=page_title,
                    storage_state_used=True,
                )
            )
        except Exception as exc:
            return {
                "detail_completed": False,
                "detail_url_opened": True,
                "detail_error": f"ingest_extractor_error: {exc}",
                "detail_completion_source": "ingest_extractor_error",
            }

        fields = payload.fields or {}
        availability_status = fields.get("availability_status") or "unknown"
        closed_reason = fields.get("closed_reason")
        return {
            "title": fields.get("title"),
            "company": fields.get("company"),
            "location_raw": fields.get("location_raw"),
            "detail_text": detail_text,
            "workplace_type_raw": fields.get("workplace_type"),
            "employment_type_raw": None,
            "is_easy_apply": fields.get("is_easy_apply"),
            "availability_status": availability_status,
            "availability_reason": closed_reason or (
                "expired_or_no_longer_accepting_applications" if availability_status == "closed" else None
            ),
            "detail_completed": True,
            "detail_url_opened": True,
            "detail_completion_source": "ingest_extractor",
            "detail_error": None,
        }

    def _prefer_ingest_extractor_detail(self, dom_detail: dict[str, Any], extractor_detail: dict[str, Any]) -> dict[str, Any]:
        merged = dict(dom_detail or {})
        for key in ("title", "company", "location_raw", "is_easy_apply", "workplace_type_raw", "employment_type_raw"):
            value = extractor_detail.get(key)
            if value not in (None, ""):
                merged[key] = value
        if extractor_detail.get("detail_text") and not merged.get("detail_text"):
            merged["detail_text"] = extractor_detail["detail_text"]
        if extractor_detail.get("availability_status") == "closed":
            merged["availability_status"] = "closed"
            merged["availability_reason"] = extractor_detail.get("availability_reason")
        merged["detail_url_opened"] = True
        merged["detail_completed"] = all(merged.get(key) for key in ("title", "company", "location_raw"))
        merged["detail_completion_source"] = (
            "ingest_extractor" if merged["detail_completed"] else merged.get("detail_completion_source") or "dom_selectors"
        )
        if extractor_detail.get("detail_error"):
            merged["detail_error"] = extractor_detail["detail_error"]
        return merged

    def _should_complete_from_job_url(self, card: dict[str, Any]) -> bool:
        if not card.get("linkedin_job_url"):
            return False
        if card.get("availability_status") == "closed":
            return False
        return not all(card.get(key) for key in ("title", "company", "location_raw"))

    def _merge_detail(self, card: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
        if not detail:
            return card
        merged = dict(card)
        for key in ("title", "company", "location_raw", "is_easy_apply"):
            if merged.get(key) in (None, "") and detail.get(key) not in (None, ""):
                merged[key] = detail[key]
        merged["detail_text"] = detail.get("detail_text") or merged.get("detail_text")
        merged["workplace_type_raw"] = detail.get("workplace_type_raw") or merged.get("workplace_type_raw")
        merged["employment_type_raw"] = detail.get("employment_type_raw") or merged.get("employment_type_raw")
        merged["detail_error"] = detail.get("detail_error")
        merged["detail_completion_source"] = detail.get("detail_completion_source") or merged.get("detail_completion_source")
        if detail.get("availability_status") == "closed":
            merged["availability_status"] = "closed"
            merged["availability_reason"] = detail.get("availability_reason")
        merged["detail_completed"] = bool(detail.get("detail_completed")) and all(
            merged.get(key) for key in ("title", "company", "location_raw")
        )
        merged["detail_url_opened"] = bool(detail.get("detail_url_opened"))
        return merged
    async def _save_debug_artifacts(self, url: str, html: str) -> None:
        assert self.page is not None
        debug_dir = Path("data/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        safe_name = str(abs(hash(url)))
        html_path = debug_dir / f"linkedin_search_{safe_name}.html"
        png_path = debug_dir / f"linkedin_search_{safe_name}.png"
        html_path.write_text(html, encoding="utf-8")
        try:
            await self.page.screenshot(path=str(png_path), full_page=True)
            self.last_debug_screenshot_path = str(png_path)
        except Exception:
            self.last_debug_screenshot_path = None
        self.last_debug_html_path = str(html_path)


def load_search_urls_from_file(path: str) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Search URL file must contain a list of objects.")
    normalized: list[dict] = []
    for item in payload:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        normalized.append({
            "name": item.get("name") or item["url"],
            "url": item["url"],
            "enabled": bool(item.get("enabled", True)),
        })
    return normalized
