import json
from pathlib import Path

from src.utils.storage import _validate_ai_log_payload, save_ai_response


def test_save_ai_response_persists_provider_metadata_and_error(tmp_path: Path):
    log_path = tmp_path / "ai_log.jsonl"

    payload = save_ai_response(
        prompt="oi",
        response="teste",
        provider="gemini",
        chat_url="https://gemini.google.com/app/123",
        metadata={"selector_used": "div[contenteditable='true']"},
        error=None,
        log_path=log_path,
    )

    assert payload["provider"] == "gemini"
    line = log_path.read_text(encoding="utf-8").strip()
    data = json.loads(line)
    assert data["provider"] == "gemini"
    assert data["metadata"]["selector_used"] == "div[contenteditable='true']"
    assert data["success"] is True


def test_validate_ai_log_payload_normalizes_unexpected_types():
    payload = _validate_ai_log_payload(
        {
            "provider": None,
            "prompt": 123,
            "response": 456,
            "chat_url": 789,
            "success": 1,
            "metadata": "bad",
            "error": 999,
        }
    )

    assert payload["provider"] == "unknown"
    assert payload["prompt"] == "123"
    assert payload["response"] == "456"
    assert payload["chat_url"] == "789"
    assert payload["metadata"] == {}
    assert payload["error"] == "999"
