import argparse
import asyncio
import json

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.db.session import init_db
from src.services.linkedin_search_collection_service import (
    collect_jobs_from_search_urls,
    summarize_cards,
)
from src.services.linkedin_search_ingest_service import collect_and_ingest_search_jobs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Coleta vagas de URLs de busca do LinkedIn. Por padrão apenas gera auditoria/Excel; "
            "use --ingest para gravar as vagas abertas na tabela Job."
        )
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Depois de coletar os cards, ingere vagas abertas usando o mesmo fluxo do POST /ingest-url.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Com --ingest, simula quais vagas seriam ingeridas, sem gravar no banco.",
    )
    parser.add_argument(
        "--max-jobs-per-url",
        type=int,
        default=None,
        help="Limita a quantidade de cards processados por URL de busca.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Com --ingest, interrompe no primeiro erro de ingestão.",
    )
    parser.add_argument(
        "--include-closed",
        action="store_true",
        help="Com --ingest, tenta processar vagas marcadas como fechadas/expiradas. Por padrão elas são ignoradas.",
    )
    parser.add_argument(
        "--no-export-xlsx",
        action="store_true",
        help="Não exporta o Excel de auditoria dos cards capturados.",
    )
    parser.add_argument(
        "--export-xlsx-path",
        default=None,
        help="Caminho opcional para salvar o Excel de auditoria.",
    )
    return parser


async def run_collect_only(args: argparse.Namespace) -> dict:
    items = await collect_jobs_from_search_urls(
        max_jobs_per_url=args.max_jobs_per_url,
        export_xlsx=not args.no_export_xlsx,
        export_xlsx_path=args.export_xlsx_path,
    )
    return {
        "mode": "collect",
        "status": "completed",
        "summary": summarize_cards(items),
        "items": items,
    }


async def run_collect_and_ingest(args: argparse.Namespace) -> dict:
    settings = get_settings()
    await init_db()
    engine = create_async_engine(settings.database_url, future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with SessionLocal() as session:
            return await collect_and_ingest_search_jobs(
                session=session,
                max_jobs_per_url=args.max_jobs_per_url,
                continue_on_error=not args.stop_on_error,
                skip_closed=not args.include_closed,
                export_xlsx=not args.no_export_xlsx,
                export_xlsx_path=args.export_xlsx_path,
                dry_run=args.dry_run,
            )
    finally:
        await engine.dispose()


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.dry_run and not args.ingest:
        parser.error("--dry-run só faz sentido junto com --ingest.")

    result = await run_collect_and_ingest(args) if args.ingest else await run_collect_only(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
