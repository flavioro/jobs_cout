from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import Any

from src.adapters.ai_web.base.exceptions import (
    AIWebPromptInputNotFound,
    AIWebResponseNotFound,
)
from src.adapters.ai_web.base.models import AIChatOptions, AIResponse
from src.core.config import get_settings


class BaseAIWebFetcher:
    provider_name: str = "unknown"
    app_url_setting_name: str = ""
    chat_mode_setting_name: str = ""
    chat_url_setting_name: str = ""
    response_wait_setting_name: str = ""
    prompt_timeout_setting_name: str = ""
    debug_prefix: str = "ai"
    selectors: dict[str, list[str]]

    def __init__(self, page):
        self.page = page
        self.settings = get_settings()

    def build_options(self, options: AIChatOptions | None = None) -> AIChatOptions:
        resolved = options.normalized() if options else AIChatOptions().normalized()
        mode = getattr(self.settings, self.chat_mode_setting_name, resolved.mode)
        chat_url = getattr(self.settings, self.chat_url_setting_name, resolved.existing_chat_url)
        response_timeout = getattr(
            self.settings,
            self.response_wait_setting_name,
            resolved.response_timeout_s,
        )
        built = AIChatOptions(
            mode=resolved.mode if options else mode,
            existing_chat_url=resolved.existing_chat_url if options else chat_url,
            max_retries=resolved.max_retries,
            response_timeout_s=resolved.response_timeout_s if options else float(response_timeout),
            force_new_chat=resolved.force_new_chat,
        )
        return built.normalized()

    async def _first_visible_locator(self, selectors: list[str], timeout_ms: int):
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                await locator.wait_for(state="visible", timeout=timeout_ms)
                return locator, selector
            except Exception:
                continue
        return None, None

    async def _count_existing_responses(self) -> int:
        max_count = 0
        for selector in self.selectors.get("response_blocks", []):
            try:
                count = await self.page.locator(selector).count()
                if count > max_count:
                    max_count = count
            except Exception:
                continue
        return max_count

    async def _extract_response_from_index(self, start_index: int) -> tuple[str, str | None]:
        for selector in self.selectors.get("response_blocks", []):
            locator = self.page.locator(selector)
            try:
                count = await locator.count()
            except Exception:
                continue
            if count <= start_index:
                continue
            texts: list[str] = []
            for index in range(start_index, count):
                try:
                    text = (await locator.nth(index).inner_text()).strip()
                except Exception:
                    continue
                cleaned = self.clean_response_text(text)
                if cleaned:
                    texts.append(cleaned)
            if texts:
                return texts[-1], selector
        return "", None

    async def _wait_for_new_response(
        self,
        *,
        before_count: int,
        timeout_s: float,
    ) -> tuple[str, str | None]:
        deadline = time.perf_counter() + timeout_s
        latest_text = ""
        latest_selector: str | None = None

        while time.perf_counter() < deadline:
            text, selector = await self._extract_response_from_index(before_count)
            if text:
                return text, selector
            if selector:
                latest_selector = selector
            await asyncio.sleep(0.25)

        return latest_text, latest_selector

    def clean_response_text(self, text: str) -> str:
        blocked_exact = {
            "show thinking",
            "hide thinking",
            "copy",
            "share",
            "editar",
            "edit",
            "good response",
            "bad response",
            "retry",
            "thumbs up",
            "thumbs down",
        }
        blocked_patterns = [
            r"^copied$",
            r"^regenerate$",
            r"^read aloud$",
            r"^listen$",
            r"^expand to view model thoughts$",
            r"^collapse model thoughts$",
            r"^show drafts$",
            r"^export$",
        ]

        lines: list[str] = []
        for raw_line in text.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line:
                continue
            lowered = line.lower()
            if lowered in blocked_exact:
                continue
            if any(re.match(pattern, lowered) for pattern in blocked_patterns):
                continue
            lines.append(line)

        cleaned = "\n".join(lines).strip()
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned

    async def _open_target(self, options: AIChatOptions) -> str:
        mode = options.resolved_mode()
        target_url = getattr(self.settings, self.app_url_setting_name)
        if mode == "existing_chat":
            if not options.existing_chat_url:
                raise AIWebPromptInputNotFound(
                    f"Existing chat mode requires a chat URL for provider '{self.provider_name}'."
                )
            target_url = options.existing_chat_url
        await self.page.goto(target_url, wait_until="domcontentloaded")
        try:
            await self.page.wait_for_load_state("load", timeout=10000)
        except Exception:
            pass
        await asyncio.sleep(1)
        if mode == "new_chat" or options.force_new_chat:
            await self.open_new_chat_if_supported()
        return target_url

    async def open_new_chat_if_supported(self) -> None:
        selectors = self.selectors.get("new_chat", [])
        if not selectors:
            return
        locator, _ = await self._first_visible_locator(selectors, timeout_ms=2000)
        if locator is not None:
            try:
                await locator.click()
                await asyncio.sleep(0.5)
            except Exception:
                return

    async def submit_prompt(self, prompt: str, options: AIChatOptions | None = None) -> AIResponse:
        resolved_options = self.build_options(options)
        prompt_timeout_ms = int(getattr(self.settings, self.prompt_timeout_setting_name))
        debug_dir = Path("data/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        retries = 0
        last_error: Exception | None = None
        attempt_history: list[dict[str, Any]] = []

        try:
            while retries <= resolved_options.max_retries:
                attempt_started = time.perf_counter()
                try:
                    target_url = await self._open_target(resolved_options)
                    before_count = await self._count_existing_responses()

                    prompt_locator, selector_used = await self._first_visible_locator(
                        self.selectors["prompt_input"],
                        timeout_ms=prompt_timeout_ms,
                    )
                    if prompt_locator is None:
                        raise AIWebPromptInputNotFound(
                            f"Prompt input not found for provider '{self.provider_name}'."
                        )

                    await self.fill_prompt(prompt_locator, prompt)
                    send_strategy = await self.send_prompt()
                    await self.wait_until_response_complete(resolved_options)

                    text, response_selector = await self._wait_for_new_response(
                        before_count=before_count,
                        timeout_s=resolved_options.response_timeout_s,
                    )
                    if not text:
                        raise AIWebResponseNotFound(
                            f"No new response found for provider '{self.provider_name}'."
                        )

                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    attempt_history.append(
                        {
                            "attempt": retries + 1,
                            "status": "success",
                            "elapsed_ms": int((time.perf_counter() - attempt_started) * 1000),
                            "before_count": before_count,
                        }
                    )
                    return AIResponse(
                        text=text,
                        provider=self.provider_name,
                        chat_url=self.page.url,
                        metadata={
                            "chat_mode": resolved_options.resolved_mode(),
                            "selector_used": selector_used,
                            "response_selector": response_selector,
                            "send_strategy": send_strategy,
                            "target_url": target_url,
                            "elapsed_ms": elapsed_ms,
                            "retries": retries,
                            "attempt_history": attempt_history,
                        },
                    )
                except Exception as exc:
                    last_error = exc
                    attempt_history.append(
                        {
                            "attempt": retries + 1,
                            "status": "retry",
                            "error": str(exc),
                            "elapsed_ms": int((time.perf_counter() - attempt_started) * 1000),
                        }
                    )
                    retries += 1
                    if retries > resolved_options.max_retries:
                        break
                    await self.recover_from_retry(retries, resolved_options)

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return AIResponse(
                text="",
                provider=self.provider_name,
                chat_url=self.page.url,
                success=False,
                error=str(last_error) if last_error else "Unknown browser AI error",
                metadata={
                    "chat_mode": resolved_options.resolved_mode(),
                    "elapsed_ms": elapsed_ms,
                    "retries": retries,
                    "attempt_history": attempt_history,
                },
            )
        finally:
            content = await self.page.content()
            (debug_dir / f"{self.debug_prefix}_page.html").write_text(content, encoding="utf-8")
            await self.page.screenshot(
                path=str(debug_dir / f"{self.debug_prefix}_page.png"),
                full_page=True,
            )

    async def recover_from_retry(self, retries: int, options: AIChatOptions | None = None) -> None:
        try:
            await self.page.reload(wait_until="domcontentloaded")
        except Exception:
            try:
                target_url = None
                if options and options.resolved_mode() == "existing_chat" and options.existing_chat_url:
                    target_url = options.existing_chat_url
                elif self.app_url_setting_name:
                    target_url = getattr(self.settings, self.app_url_setting_name)
                if target_url:
                    await self.page.goto(target_url, wait_until="domcontentloaded")
            except Exception:
                pass
        await asyncio.sleep(min(1.0 * retries, 2.0))

    async def fill_prompt(self, prompt_locator, prompt: str) -> None:
        await prompt_locator.click()
        await prompt_locator.fill(prompt)

    async def send_prompt(self) -> str:
        send_locator, send_selector = await self._first_visible_locator(
            self.selectors.get("send_button", []),
            1500,
        )
        if send_locator is not None:
            await send_locator.click()
            return send_selector or "send_button"
        await self.page.keyboard.press("Enter")
        return "keyboard_enter"

    async def wait_until_response_complete(self, options: AIChatOptions) -> None:
        stop_locator, _ = await self._first_visible_locator(self.selectors.get("stop_button", []), 3000)
        if stop_locator is not None:
            try:
                await stop_locator.wait_for(
                    state="hidden",
                    timeout=int(options.response_timeout_s * 1000),
                )
                await asyncio.sleep(0.8)
                return
            except Exception:
                pass
        await asyncio.sleep(options.response_timeout_s)
