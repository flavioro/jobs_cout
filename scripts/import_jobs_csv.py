import argparse
import asyncio
import json

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.db.session import init_db
from src.services.batch_ingest_service import ingest_jobs_from_csv


async def main() -> None:
    parser = argparse.ArgumentParser(description="Importa vagas de um CSV e processa em lote usando uma única sessão do navegador.")
    parser.add_argument("--csv-path", default=None, help="Caminho do CSV. Se omitido, usa o path configurado no .env.")
    parser.add_argument("--status-filter", default=None, help="Status a filtrar. Ex: new")
    parser.add_argument("--include-all-statuses", action="store_true", help="Processa todas as linhas válidas ignorando o status.")
    parser.add_argument("--limit", type=int, default=None, help="Limita a quantidade de vagas processadas.")
    parser.add_argument("--dry-run", action="store_true", help="Apenas valida e mostra o que seria processado.")
    parser.add_argument("--stop-on-error", action="store_true", help="Interrompe no primeiro erro.")
    args = parser.parse_args()

    settings = get_settings()
    await init_db()
    engine = create_async_engine(settings.database_url, future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with SessionLocal() as session:
            result = await ingest_jobs_from_csv(
                session=session,
                csv_path=args.csv_path,
                status_filter=args.status_filter,
                include_all_statuses=args.include_all_statuses,
                limit=args.limit,
                dry_run=args.dry_run,
                continue_on_error=not args.stop_on_error,
            )
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
