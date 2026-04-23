"""Prompts centralizados para provedores de IA via navegador.

Este módulo concentra prompts operacionais para ChatGPT, Gemini e futuros providers.
Evita texto solto em scripts e facilita versionamento.
"""

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
        "test_connection": "Responda apenas com a palavra OK.",
    },
    "gemini": {
        "test_connection": 'Responda em JSON válido: {{"status":"ok","provider":"gemini"}}',
    },
}


def get_ai_prompt(name: str, provider: str | None = None, **kwargs: Any) -> str:
    provider_key = (provider or "shared").strip().lower()
    prompt_template = AI_PROMPTS.get(provider_key, {}).get(name) or AI_PROMPTS["shared"][name]
    return prompt_template.format(**kwargs)
