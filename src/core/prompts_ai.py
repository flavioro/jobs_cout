"""Prompts centralizados para provedores de IA via navegador."""

from typing import Any

AI_PROMPTS: dict[str, dict[str, str]] = {
    "shared": {
        "test_connection": "Responda apenas com a palavra OK.",
        "job_analysis": (
            "Analise a seguinte vaga de emprego e retorne um JSON com: "
            "setor_principal, senioridade, tecnologias_principais (máx. 5) e resumo. "
            "Vaga: {job_description}"
        ),
    },
    "chatgpt": {
        "test_connection": "Responda apenas com a palavra TESTE_OK.",
    },
    "gemini": {
        "test_connection": "Responda apenas com a palavra TESTE_OK.",
    },
}

PROMPTS = AI_PROMPTS["shared"]


def get_ai_prompt(name: str, provider: str | None = None, **kwargs: Any) -> str:
    provider_key = (provider or "shared").strip().lower()
    prompt_template = AI_PROMPTS.get(provider_key, {}).get(name) or AI_PROMPTS["shared"][name]
    if kwargs:
        return prompt_template.format(**kwargs)
    return prompt_template
