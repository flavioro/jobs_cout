import argparse
import asyncio
import json

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.db.session import init_db
from src.services.job_candidate_service import process_pending_job_candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Processa candidatos pendentes da tabela job_candidates e cria/atualiza registros na tabela Job."
    )
    parser.add_argument("--source", default="linkedin", help="Fonte dos candidatos. Padrão: linkedin.")
    parser.add_argument("--limit", type=int, default=20, help="Quantidade máxima de candidatos para processar.")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar Jobs nem alterar candidatos.")
    parser.add_argument("--retry-failed", action="store_true", help="Inclui candidatos com processing_status=failed.")
    parser.add_argument("--include-closed", action="store_true", help="Tenta processar vagas fechadas/expiradas.")
    parser.add_argument("--stop-on-error", action="store_true", help="Interrompe no primeiro erro.")
    return parser


async def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    await init_db()
    engine = create_async_engine(settings.database_url, future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with SessionLocal() as session:
            result = await process_pending_job_candidates(
                session=session,
                source=args.source,
                limit=args.limit,
                dry_run=args.dry_run,
                retry_failed=args.retry_failed,
                skip_closed=not args.include_closed,
                continue_on_error=not args.stop_on_error,
            )
    finally:
        await engine.dispose()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
