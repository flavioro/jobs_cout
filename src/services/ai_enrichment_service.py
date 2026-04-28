
import json
import structlog
import unicodedata
from json import JSONDecodeError

try:
    import dspy
except ModuleNotFoundError:
    class _DSPYStub:
        class Signature: ...
        class InputField:
            def __init__(self, *args, **kwargs):
                pass
        class OutputField:
            def __init__(self, *args, **kwargs):
                pass
    dspy = _DSPYStub()

try:
    from groq import AsyncGroq
except ModuleNotFoundError:
    class AsyncGroq:  # pragma: no cover - fallback only
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError("groq package is required for runtime enrichment")

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.ai_web.base.models import AIChatOptions
from src.core.config import get_settings
from src.core.enums import EnglishLevel, SeniorityLevel, JobSector
from src.core.prompts import ENRICHMENT_SYSTEM_PROMPT
from src.core.prompts_enrichment import build_web_enrichment_prompt
from src.schemas.ai import GroqJobAnalysis
from src.schemas.jobs import EnrichmentFilters
from src.services.browser_ai_service import BrowserAIProviderSession
from src.services.persistence_service import (
    delete_job,
    get_pending_jobs_for_enrichment,
    save_blocked_job,
    update_job_ai_enrichment,
)
from src.utils.text import find_blocking_keyword

logger = structlog.get_logger(__name__)

# Keep exact values centralized to avoid coupling to enum member names.
JOB_SECTOR_VALUES = {
    "it_consulting": "Consultoria de TI e Outsourcing",
    "software_saas": "Produto de Software e SaaS",
    "cybersecurity": "Cibersegurança",
    "data_ai": "Dados e Inteligência Artificial",
    "finance_fintech": "Finanças, Bancos e Fintechs",
    "retail_ecommerce": "Varejo e E-commerce",
    "health_healthtech": "Saúde e Healthtechs",
    "education_edtech": "Educação e Edtechs",
    "industry_manufacturing": "Indústria e Manufatura",
    "logistics_supply": "Logística e Supply Chain",
    "public_sector": "Setor Público e Governo",
    "agribusiness": "Agronegócio",
    "other": "Outros",
    "unknown": "Desconhecido",
}


class ExtractJobDetails(dspy.Signature):
    """Analise o título, empresa e descrição da vaga para extrair informações estruturadas."""

    title: str = dspy.InputField(desc="O título original da vaga.")
    company: str = dspy.InputField(desc="O nome da empresa contratante.")
    description_text: str = dspy.InputField(desc="O corpo de texto completo da vaga.")

    seniority_normalized: SeniorityLevel = dspy.OutputField(
        desc="Classifique o nível de senioridade exigido. Responda apenas com os valores permitidos do enum."
    )

    sector: JobSector = dspy.OutputField(
        desc=(
            "Analise a descrição e o nome da empresa e classifique o setor de atuação. "
            "Se a empresa for uma fábrica fazendo software internamente, escolha 'Indústria'. "
            "Se for uma software house, escolha 'Produto de Software' ou 'Consultoria'. "
            "Responda EXATAMENTE com um dos valores permitidos do enum."
        )
    )


def _resolve_enrichment_provider(settings) -> str:
    value = getattr(settings, "enrichment_provider", None)
    if value is None:
        return "groq"
    normalized = str(value).strip().lower()
    return normalized or "groq"


def _extract_first_json_object(text: str) -> str:
    candidate = text.strip()

    if candidate.startswith("```"):
        candidate = candidate.strip("`").strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()

    if candidate.startswith("{") and candidate.endswith("}"):
        return candidate

    start = None
    depth = 0
    for idx, ch in enumerate(candidate):
        if ch == "{":
            if start is None:
                start = idx
            depth += 1
        elif ch == "}" and start is not None:
            depth -= 1
            if depth == 0:
                return candidate[start : idx + 1]

    raise JSONDecodeError("Nenhum objeto JSON encontrado na resposta.", candidate, 0)


def _normalize_text_key(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    # Common mojibake repairs seen in logs/tests.
    repairs = {
        "nòo": "nao",
        "n�o": "nao",
        "nÃ£o": "nao",
        "não": "nao",
        "construþòo": "construcao",
        "construþao": "construcao",
        "constru��o": "construcao",
        "construã§ã£o": "construcao",
    }
    for bad, good in repairs.items():
        raw = raw.replace(bad, good)

    normalized = unicodedata.normalize("NFKD", raw)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace("/", " ").replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    return normalized


def _normalize_sector_value(value: str | None) -> str:
    raw = _normalize_text_key(value)
    if not raw:
        return JOB_SECTOR_VALUES["unknown"]

    exact_values = {
        _normalize_text_key(item.value): item.value
        for item in JobSector
    }
    if raw in exact_values:
        return exact_values[raw]

    if "consultoria" in raw or "outsourcing" in raw:
        return JOB_SECTOR_VALUES["it_consulting"]
    if "software" in raw or "saas" in raw or "produto digital" in raw:
        return JOB_SECTOR_VALUES["software_saas"]
    if "ciber" in raw or "seguranca" in raw or "cyber" in raw:
        return JOB_SECTOR_VALUES["cybersecurity"]
    if "dados" in raw or "inteligencia artificial" in raw or raw == "ia" or " machine learning" in f" {raw} " or " ai " in f" {raw} ":
        return JOB_SECTOR_VALUES["data_ai"]
    if "finan" in raw or "banco" in raw or "bank" in raw or "fintech" in raw:
        return JOB_SECTOR_VALUES["finance_fintech"]
    if "varejo" in raw or "e commerce" in raw or "ecommerce" in raw:
        return JOB_SECTOR_VALUES["retail_ecommerce"]
    if "saude" in raw or "health" in raw or "healthtech" in raw:
        return JOB_SECTOR_VALUES["health_healthtech"]
    if "educa" in raw or "edtech" in raw:
        return JOB_SECTOR_VALUES["education_edtech"]
    if "industr" in raw or "manufatura" in raw or "construcao civil" in raw:
        return JOB_SECTOR_VALUES["industry_manufacturing"]
    if "logist" in raw or "supply" in raw:
        return JOB_SECTOR_VALUES["logistics_supply"]
    if "setor publico" in raw or "governo" in raw:
        return JOB_SECTOR_VALUES["public_sector"]
    if "agro" in raw:
        return JOB_SECTOR_VALUES["agribusiness"]
    if "outro" in raw:
        return JOB_SECTOR_VALUES["other"]

    return JOB_SECTOR_VALUES["unknown"]


def _normalize_english_level(value: str | None) -> str:
    raw = _normalize_text_key(value)
    if not raw:
        return EnglishLevel.NOT_MENTIONED.value

    exact_values = {item.value.lower(): item.value for item in EnglishLevel}
    if raw in exact_values:
        return exact_values[raw]

    if "nao mencionado" in raw or "not mentioned" in raw or "not specified" in raw:
        return EnglishLevel.NOT_MENTIONED.value
    if "flu" in raw:
        return EnglishLevel.FLUENT.value
    if "avan" in raw or "advanced" in raw:
        return EnglishLevel.ADVANCED.value
    if "inter" in raw:
        return EnglishLevel.INTERMEDIATE.value
    if "basic" in raw or "basico" in raw:
        return EnglishLevel.BASIC.value

    return EnglishLevel.NOT_MENTIONED.value


def _normalize_seniority_suggestion(value: str | None) -> str | None:
    raw = _normalize_text_key(value)
    if not raw:
        return None

    if raw in {"none", "unknown", "desconhecido", "nao mencionado", "not mentioned"}:
        return None
    if "staff" in raw:
        return "staff"
    if "senior" in raw or raw == "sr":
        return "senior"
    if "pleno" in raw or "mid" in raw or "middle" in raw:
        return "mid"
    if "junior" in raw or raw == "jr":
        return "junior"
    if "intern" in raw or "estag" in raw:
        return "intern"

    return raw


def _normalize_web_analysis_payload(content: str) -> str:
    payload = json.loads(content)
    payload["sector"] = _normalize_sector_value(payload.get("sector"))
    payload["english_level"] = _normalize_english_level(payload.get("english_level"))
    payload["seniority_suggestion"] = _normalize_seniority_suggestion(payload.get("seniority_suggestion"))
    return json.dumps(payload, ensure_ascii=False)


async def _run_groq_enrichment(job, settings, client: AsyncGroq | None):
    if client is None:
        api_key = settings.groq_api_key or "missing-groq-api-key"
        if not settings.groq_api_key:
            logger.warning("groq_api_key_missing", fallback=True)
        client = AsyncGroq(api_key=api_key)

    job_context = {
        "title": job.title,
        "seniority_current": job.seniority_normalized,
        "description": job.description_text[:6000] if job.description_text else "",
    }

    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": ENRICHMENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Avalie a seguinte vaga para o candidato com este perfil:\n\n"
                    f"PERFIL: {settings.user_profile_context}\n\n"
                    f"VAGA (JSON):\n{json.dumps(job_context)}"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    analysis = GroqJobAnalysis.model_validate_json(content)
    return analysis, client


async def _run_browser_enrichment(job, settings, browser_session: BrowserAIProviderSession, provider_name: str):
    prompt = build_web_enrichment_prompt(
        title=job.title,
        company=job.company,
        description_text=job.description_text,
        current_seniority=job.seniority_normalized,
        user_profile_context=settings.user_profile_context,
    )
    options = AIChatOptions(
        mode=getattr(settings, "enrichment_web_chat_mode", "new_chat"),
        max_retries=int(getattr(settings, "enrichment_web_max_retries", 1)),
        response_timeout_s=float(getattr(settings, "enrichment_web_response_timeout_s", 45.0)),
        force_new_chat=bool(getattr(settings, "enrichment_web_force_new_chat", True)),
    )
    response = await browser_session.run_prompt(prompt, options=options)
    if not response.success:
        raise RuntimeError(response.error or f"{provider_name} web enrichment failed")

    content = _extract_first_json_object(response.text)
    normalized_content = _normalize_web_analysis_payload(content)
    analysis = GroqJobAnalysis.model_validate_json(normalized_content)
    return analysis


async def enrich_pending_jobs(session: AsyncSession, limit: int = 10, filters: EnrichmentFilters | None = None) -> dict:
    settings = get_settings()
    provider = _resolve_enrichment_provider(settings)

    jobs_to_process = await get_pending_jobs_for_enrichment(session, limit=limit, filters=filters)
    if not jobs_to_process:
        logger.info("ai_enrichment.no_jobs_found")
        return {
            "status": "success",
            "provider": provider,
            "processed": 0,
            "blocked": 0,
            "failed": 0,
            "details": [],
        }

    results = []
    processed = 0
    failed = 0
    blocked = 0
    groq_client = None

    browser_session_cm = None
    if provider in {"chatgpt_web", "gemini_web"}:
        browser_provider = provider.replace("_web", "")
        browser_session_cm = BrowserAIProviderSession(browser_provider)

    if browser_session_cm is None:
        class _NoopContext:
            async def __aenter__(self):
                return None
            async def __aexit__(self, exc_type, exc, tb):
                return None
        browser_session_cm = _NoopContext()

    async with browser_session_cm as browser_session:
        for job in jobs_to_process:
            try:
                blocked_word = find_blocking_keyword(job.title, settings.parsed_title_blocklist)
                if blocked_word:
                    reason_text = f"Palavra bloqueada no enriquecimento: '{blocked_word}'"
                    await save_blocked_job(
                        session=session,
                        source=job.source,
                        url=job.url,
                        title=job.title,
                        company=job.company,
                        block_reason=reason_text,
                    )
                    await delete_job(session, job.id)
                    blocked += 1
                    results.append({"job_id": job.id, "status": "blocked"})
                    logger.info("ai_enrichment.blocked", job_id=job.id, reason=reason_text)
                    continue

                if provider == "groq":
                    analysis, groq_client = await _run_groq_enrichment(job, settings, groq_client)
                elif provider in {"chatgpt_web", "gemini_web"}:
                    analysis = await _run_browser_enrichment(job, settings, browser_session, provider)
                else:
                    raise ValueError(f"Provider de enrichment não suportado: {provider}")

                try:
                    english_enum = EnglishLevel((analysis.english_level or "").lower())
                except ValueError:
                    english_enum = EnglishLevel.NOT_MENTIONED

                seniority_to_update = None
                if (
                    not job.seniority_normalized
                    and analysis.seniority_suggestion
                    and analysis.seniority_suggestion.lower() != "none"
                ):
                    seniority_to_update = analysis.seniority_suggestion.lower()

                await update_job_ai_enrichment(
                    session=session,
                    job_id=job.id,
                    fit_score=analysis.fit_score,
                    fit_rationale=analysis.fit_rationale,
                    skills=analysis.skills,
                    english_level=english_enum,
                    seniority_normalized=seniority_to_update,
                    sector=analysis.sector,
                )

                processed += 1
                results.append({
                    "job_id": job.id,
                    "title": job.title,
                    "fit_score": analysis.fit_score,
                    "status": "success",
                })
                logger.info("ai_enrichment.success", job_id=job.id, fit_score=analysis.fit_score, provider=provider)

            except (json.JSONDecodeError, ValidationError, JSONDecodeError) as exc:
                failed += 1
                results.append({"job_id": job.id, "status": "json_parsing_error"})
                logger.error("ai_enrichment.json_error", job_id=job.id, error=str(exc), provider=provider)
            except Exception as exc:
                failed += 1
                results.append({"job_id": job.id, "status": "api_error"})
                logger.error("ai_enrichment.api_error", job_id=job.id, error=str(exc), provider=provider)

    return {
        "status": "completed",
        "provider": provider,
        "processed": processed,
        "blocked": blocked,
        "failed": failed,
        "details": results,
    }
