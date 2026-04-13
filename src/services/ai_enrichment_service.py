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

logger = structlog.get_logger(__name__)

# Schema interno para validar a resposta exata da Groq
class GroqJobAnalysis(BaseModel):
    skills: list[str]
    fit_score: int
    fit_rationale: str
    salary_raw: str | None
    english_level: str


async def enrich_pending_jobs(session: AsyncSession, limit: int = 10, filters: EnrichmentFilters | None = None) -> dict:
    settings = get_settings()
    
    if not settings.groq_api_key:
        logger.error("groq_api_key_missing")
        return {"error": "GROQ_API_KEY não configurada no .env"}

    client = AsyncGroq(api_key=settings.groq_api_key)

    jobs_to_process = await get_pending_jobs_for_enrichment(session, limit=limit, filters=filters)

    if not jobs_to_process:
        return {"message": "Nenhuma vaga pendente de enriquecimento encontrada.", "processed": 0, "blocked": 0}

    processed = 0
    blocked = 0
    failed = 0
    results = []

    # O Prompt de Sistema que dita as regras do JSON e do Perfil
    system_prompt = f"""
    Você é um assistente de recrutamento especializado em TI (Agentic AI).
    Sua missão é extrair dados de descrições de vagas de emprego e avaliar a compatibilidade (Match) com o candidato.
    
    PERFIL DO CANDIDATO:
    {settings.user_profile_context}
    
    INSTRUÇÕES DE SAÍDA:
    Você deve retornar ESTRITAMENTE um objeto JSON válido. Nenhuma palavra fora do JSON.
    O JSON deve ter exatamente a seguinte estrutura:
    {{
        "skills": ["Lista", "de", "Habilidades", "mencionadas"],
        "fit_score": <inteiro de 0 a 100 baseada na aderência ao perfil do candidato>,
        "fit_rationale": "<Texto explicando o motivo da nota, em primeira pessoa, referindo-se ao candidato como 'você'>",
        "salary_raw": "<Texto do salário se mencionado na vaga, ou null se não encontrar>",
        "english_level": "<DEVE ser um destes valores exatos: not_mentioned, none_required, basic, intermediate, advanced, fluent, implicit>"
    }}
    
    REGRAS DO ENGLISH LEVEL:
    - implicit: Se a vaga estiver toda escrita em inglês, mas não exigir nível explicitamente.
    - not_mentioned: Se estiver em português e não falar de idiomas.
    - none_required: Se disser expressamente que não precisa de inglês.
    - Caso contrário, classifique no nível solicitado.
    """

    for job in jobs_to_process:
        # --- NOVO: SEGUNDO PORTÃO DE SEGURANÇA (BLOCKLIST) ---
        blocked_word = find_blocking_keyword(job.title, settings.parsed_title_blocklist)
        if blocked_word:
            reason = f"Bloqueio tardio no enriquecimento: '{blocked_word}'"
            logger.info("job.blocked_during_enrichment", job_id=job.id, title=job.title)
            
            # 1. Salva na tabela de bloqueadas (sem duplicar)
            await save_blocked_job(
                session=session,
                source=job.source,
                url=job.url,
                title=job.title,
                company=job.company,
                block_reason=reason
            )
            
            # 2. Remove da tabela principal de jobs
            await delete_job(session, job.id)
            
            blocked += 1
            results.append({"job_id": job.id, "title": job.title, "status": "blocked_by_title"})
            continue
        # ---------------------------------------------------

        try:
            logger.info("ai_enrichment.started", job_id=job.id, title=job.title)
            
            completion = await client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"DESCRIÇÃO DA VAGA:\n{job.description_text}"}
                ],
                temperature=0.1, # Temperatura baixa para garantir consistência no JSON
                response_format={"type": "json_object"} # Força a Groq a devolver apenas JSON
            )

            response_content = completion.choices[0].message.content
            
            # Converte a string JSON para Dicionário e depois valida com Pydantic
            raw_json = json.loads(response_content)
            analysis = GroqJobAnalysis.model_validate(raw_json)

            # Mapeamento do Enum de Inglês com fallback seguro
            try:
                english_enum = EnglishLevel(analysis.english_level.lower())
            except ValueError:
                english_enum = EnglishLevel.NOT_MENTIONED

            # Salva na Base de Dados
            await update_job_ai_enrichment(
                session=session,
                job_id=job.id,
                fit_score=analysis.fit_score,
                fit_rationale=analysis.fit_rationale,
                skills=analysis.skills,
                salary_raw=analysis.salary_raw,
                english_level=english_enum
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
        "requested_limit": limit,
        "processed": processed,
        "blocked": blocked,
        "failed": failed,
        "items": results
    }