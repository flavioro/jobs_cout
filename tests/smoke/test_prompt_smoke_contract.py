import pytest

from src.core.prompts_ai import get_ai_prompt


@pytest.mark.smoke
def test_smoke_prompt_contract():
    assert get_ai_prompt("test_connection", provider="chatgpt")
    assert get_ai_prompt("test_connection", provider="gemini")
