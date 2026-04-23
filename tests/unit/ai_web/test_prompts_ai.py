from src.core.prompts_ai import AI_PROMPTS, PROMPTS, get_ai_prompt


def test_get_ai_prompt_uses_provider_specific_prompt():
    assert get_ai_prompt("test_connection", provider="gemini") == "Responda apenas com a palavra TESTE_OK."


def test_get_ai_prompt_falls_back_to_shared():
    value = get_ai_prompt("job_analysis", provider="chatgpt", job_description="Python")
    assert "Python" in value
    assert "tecnologias_principais" in value


def test_prompts_alias_kept_for_legacy_scripts():
    assert PROMPTS is AI_PROMPTS["shared"]
