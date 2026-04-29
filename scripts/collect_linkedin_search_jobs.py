import asyncio
import json

from src.core.config import get_settings
from src.services.linkedin_search_collection_service import collect_jobs_from_search_urls, summarize_cards


async def main() -> None:
    settings = get_settings()
    items = await collect_jobs_from_search_urls()
    summary = summarize_cards(items)
    print(json.dumps({
        "summary": summary,
        "cards_xlsx_path": settings.linkedin_search_export_xlsx_path if settings.linkedin_search_export_xlsx_enabled else None,
        "items": items,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
