import asyncio
import structlog
from sqlalchemy import delete, select

# CORREÇÃO: Importando o AsyncSessionLocal correto da sua arquitetura
from src.db.session import AsyncSessionLocal 
from src.db.models import Job, RelatedJob

logger = structlog.get_logger(__name__)

async def remove_unlogged_jobs():
    """Remove vagas inseridas indevidamente com a tela de login do LinkedIn."""
    # CORREÇÃO: Usando o AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        # 1. Contar quantas vagas serão afetadas
#        stmt_select = select(Job).where(Job.title == "Olá novamente")
        stmt_select = select(Job).where(Job.title == "Entrar")
        bad_jobs = (await session.execute(stmt_select)).scalars().all()
        
        if not bad_jobs:
            logger.info("Nenhuma vaga inválida encontrada no banco.")
            return

        logger.info(f"Encontradas {len(bad_jobs)} vagas inválidas. Iniciando exclusão...")

        # 2. Apagamos as vagas relacionadas primeiro para não quebrar a chave estrangeira
        bad_job_ids = [job.id for job in bad_jobs]
        
        stmt_delete_related = delete(RelatedJob).where(RelatedJob.parent_job_id.in_(bad_job_ids))
        await session.execute(stmt_delete_related)

        # 3. Apagamos as vagas principais
        stmt_delete_jobs = delete(Job).where(Job.id.in_(bad_job_ids))
        result = await session.execute(stmt_delete_jobs)
        
        await session.commit()
        logger.info(f"Limpeza concluída! {result.rowcount} vagas removidas com sucesso.")

if __name__ == "__main__":
    asyncio.run(remove_unlogged_jobs())