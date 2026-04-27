from __future__ import annotations

from src.core.config import get_settings

from src.adapters.linkedin.adapter import LinkedInAdapter
from src.adapters.linkedin.fetcher import LinkedInBrowserSession
from src.schemas.jobs import CsvBatchIngestItem, CsvBatchIngestResponse
from src.services.ingest_service import ingest_linkedin_request_with_adapter
from src.services.jobs_csv_import_service import read_jobs_csv


async def ingest_jobs_from_csv(
    *,
    session,
    csv_path: str | None = None,
    status_filter: str | None = None,
    include_all_statuses: bool = False,
    limit: int | None = None,
    dry_run: bool = False,
    continue_on_error: bool = True,
) -> CsvBatchIngestResponse:
    resolved_path, jobs, total_rows = read_jobs_csv(
        csv_path,
        status_filter=status_filter,
        include_all_statuses=include_all_statuses,
        limit=limit,
    )
    effective_status_filter = None if include_all_statuses else (status_filter or get_settings().csv_import_status_filter)

    items: list[CsvBatchIngestItem] = []
    processed = 0
    success_count = 0
    failed_count = 0
    skipped_count = 0

    if dry_run:
        for job in jobs:
            items.append(
                CsvBatchIngestItem(
                    row_number=job.row_number,
                    source_status=job.source_status,
                    linkedin_job_id=job.linkedin_job_id,
                    url=job.url,
                    title=job.title,
                    selected=True,
                    ok=False,
                    skipped=True,
                    result_status="dry_run",
                )
            )
        return CsvBatchIngestResponse(
            status="dry_run",
            csv_path=str(resolved_path),
            dry_run=True,
            requested_status_filter=status_filter,
            effective_status_filter=effective_status_filter,
            total_rows=total_rows,
            selected_rows=len(jobs),
            processed=0,
            success_count=0,
            failed_count=0,
            skipped_count=len(jobs),
            items=items,
        )

    async with LinkedInBrowserSession() as browser_session:
        adapter = LinkedInAdapter(fetcher=browser_session.fetch)
        for job in jobs:
            processed += 1
            try:
                response = await ingest_linkedin_request_with_adapter(job.request, session, adapter)
                ok = response.status not in {"error", "rejected"}
                success_count += 1 if ok else 0
                failed_count += 0 if ok else 1
                items.append(
                    CsvBatchIngestItem(
                        row_number=job.row_number,
                        source_status=job.source_status,
                        linkedin_job_id=job.linkedin_job_id,
                        url=job.url,
                        title=job.title,
                        selected=True,
                        ok=ok,
                        skipped=False,
                        job_id=response.job_id,
                        result_status=response.status,
                        error=response.block_reason if getattr(response, "block_reason", None) else None,
                    )
                )
                if not ok and not continue_on_error:
                    break
            except Exception as exc:
                failed_count += 1
                items.append(
                    CsvBatchIngestItem(
                        row_number=job.row_number,
                        source_status=job.source_status,
                        linkedin_job_id=job.linkedin_job_id,
                        url=job.url,
                        title=job.title,
                        selected=True,
                        ok=False,
                        skipped=False,
                        result_status="exception",
                        error=str(exc),
                    )
                )
                if not continue_on_error:
                    break

    return CsvBatchIngestResponse(
        status="completed",
        csv_path=str(resolved_path),
        dry_run=False,
        requested_status_filter=status_filter,
        effective_status_filter=effective_status_filter,
        total_rows=total_rows,
        selected_rows=len(jobs),
        processed=processed,
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        items=items,
    )
