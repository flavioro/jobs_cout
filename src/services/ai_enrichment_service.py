import json
import structlog
from groq import AsyncGroq
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.enums import EnglishLevel
from src.services.persistence_service import (
    get_pending_jobs_for_enrichment, 
    update_job_ai_enrichment,
    save_blocked_job,
    delete_job
)
from src.utils.text import find_blocking_keyword
from src.schemas.jobs import EnrichmentFilters

# Importação do prompt centralizado
from src.core.prompts import ENRICHMENT_SYSTEM_PROMPT

logger = structlog.get_logger(__name__)

# Schema interno para validar a resposta exata da Groq
class GroqJobAnalysis(BaseModel):
    skills: list[str]
    fit_score: int
    fit_rationale: str
    seniority_suggestion: str | None
    english_level: str


async def enrich_pending_jobs(session: AsyncSession, limit: int = 10, filters: EnrichmentFilters | None = None) -> dict:
    settings = get_settings()
    
    if not settings.groq_api_key:
        logger.error("groq_api_key_missing")
        return {"error": "GROQ_API_KEY não configurada no .env"}

    client = AsyncGroq(api_key=settings.groq_api_key)

    jobs_to_process = await get_pending_jobs_for_enrichment(session, limit=limit, filters=filters)
    
    if not jobs_to_process:
        logger.info("ai_enrichment.no_jobs_found")
        return {"status": "success", "processed": 0, "blocked": 0, "failed": 0, "details": []}

    results = []
    processed = 0
    failed = 0
    blocked = 0 # CORREÇÃO: Contador de bloqueados

    for job in jobs_to_process:
        try:
            # CORREÇÃO: Lógica do Porteiro (Blocklist) reativada antes de gastar tokens da IA
            blocked_word = find_blocking_keyword(job.title, settings.parsed_title_blocklist)
            if blocked_word:
                reason_text = f"Palavra bloqueada no enriquecimento: '{blocked_word}'"
                await save_blocked_job(
                    session=session,
                    source=job.source,
                    url=job.url,
                    title=job.title,
                    company=job.company,
                    block_reason=reason_text
                )
                await delete_job(session, job.id)
                blocked += 1
                results.append({"job_id": job.id, "status": "blocked"})
                logger.info("ai_enrichment.blocked", job_id=job.id, reason=reason_text)
                continue

            # Contexto para o LLM
            job_context = {
                "title": job.title,
                "seniority_current": job.seniority_normalized,
                "description": job.description_text[:6000] if job.description_text else ""
            }

            # Chamada para a API da Groq
            response = await client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": ENRICHMENT_SYSTEM_PROMPT},
                    {
                        "role": "user", 
                        "content": f"Avalie a seguinte vaga para o candidato com este perfil:\n\nPERFIL: {settings.user_profile_context}\n\nVAGA (JSON):\n{json.dumps(job_context)}"
                    }
                ],
                response_format={"type": "json_object"}
            )

            # Extração e validação do JSON
            content = response.choices[0].message.content
            analysis = GroqJobAnalysis.model_validate_json(content)

            try:
                english_enum = EnglishLevel(analysis.english_level.lower())
            except ValueError:
                english_enum = EnglishLevel.NOT_MENTIONED

            seniority_to_update = None
            if not job.seniority_normalized and analysis.seniority_suggestion and analysis.seniority_suggestion.lower() != "none":
                seniority_to_update = analysis.seniority_suggestion.lower()

            # Salva na Base de Dados
            await update_job_ai_enrichment(
                session=session,
                job_id=job.id,
                fit_score=analysis.fit_score,
                fit_rationale=analysis.fit_rationale,
                skills=analysis.skills,
                english_level=english_enum,
                seniority_normalized=seniority_to_update
            )

            processed += 1
            results.append({"job_id": job.id, "title": job.title, "fit_score": analysis.fit_score, "status": "success"})
            logger.info("ai_enrichment.success", job_id=job.id, fit_score=analysis.fit_score)

        except (json.JSONDecodeError, ValidationError) as e:
            failed += 1
            results.append({"job_id": job.id, "status": "json_parsing_error"})
            logger.error("ai_enrichment.json_error", job_id=job.id, error=str(e))
        except Exception as e:
            failed += 1
            results.append({"job_id": job.id, "status": "api_error"})
            logger.error("ai_enrichment.api_error", job_id=job.id, error=str(e))

    return {
        "status": "completed",
        "processed": processed,
        "blocked": blocked, # CORREÇÃO: Passado no return para o teste validar
        "failed": failed,
        "details": results
    }