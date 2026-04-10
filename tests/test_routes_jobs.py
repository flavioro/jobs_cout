from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import Job, RelatedJob
from src.db.session import get_db_session
from src.main import app


def test_promote_pending_linkedin_related_jobs_endpoint_returns_summary(monkeypatch, tmp_path):
    db_path = tmp_path / "routes_jobs.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def init_data():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with SessionLocal() as session:
            parent_job_id = str(uuid.uuid4())
            session.add_all([
                Job(
                    id=parent_job_id,
                    source="linkedin",
                    external_id="999",
                    url="https://www.linkedin.com/jobs/view/999/",
                    canonical_url="https://www.linkedin.com/jobs/view/999/",
                    title="Parent",
                    company="Acme",
                    parser_used="linkedin_css_bs4",
                    parser_version="linkedin_v1.2",
                    status="success",
                    fingerprint="fp-parent",
                    collected_at=datetime.now(timezone.utc),
                ),
                RelatedJob(
                    parent_job_id=parent_job_id,
                    related_external_id="101",
                    related_url="https://www.linkedin.com/jobs/view/101/",
                    canonical_related_job_url="https://www.linkedin.com/jobs/view/101/",
                    title="Related Pending",
                    company="Company Y",
                    promotion_status="pending",
                ),
            ])
            await session.commit()

    import asyncio
    asyncio.run(init_data())

    async def override_get_db_session():
        async with SessionLocal() as session:
            yield session

    async def fake_promote_pending_linkedin_related_jobs(session, limit):
        return {
            "requested_limit": limit,
            "processed": 1,
            "promoted": 1,
            "already_resolved": 0,
            "failed": 0,
            "skipped": 0,
            "items": [
                {
                    "related_job_id": "r1",
                    "canonical_related_job_url": "https://www.linkedin.com/jobs/view/101/",
                    "promotion_status": "promoted",
                    "action": "promoted",
                    "resolved_job_id": "j1",
                    "promotion_attempts": 1,
                    "last_promotion_error": None,
                }
            ],
        }

    app.dependency_overrides[get_db_session] = override_get_db_session
    monkeypatch.setattr(
        "src.api.routes_jobs.promote_pending_linkedin_related_jobs",
        fake_promote_pending_linkedin_related_jobs,
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/linkedin/related-jobs/promote-pending",
            headers={"X-API-Key": "changeme"},
            json={"limit": 5},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["requested_limit"] == 5
        assert payload["processed"] == 1
        assert payload["promoted"] == 1
        assert payload["items"][0]["action"] == "promoted"
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_get_all_related_jobs_can_filter_by_promotion_status(tmp_path):
    db_path = tmp_path / "routes_related_jobs_filter.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def init_data():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with SessionLocal() as session:
            parent_job_id = str(uuid.uuid4())
            session.add(
                Job(
                    id=parent_job_id,
                    source="linkedin",
                    external_id="999",
                    url="https://www.linkedin.com/jobs/view/999/",
                    canonical_url="https://www.linkedin.com/jobs/view/999/",
                    title="Parent",
                    company="Acme",
                    parser_used="linkedin_css_bs4",
                    parser_version="linkedin_v1.2",
                    status="success",
                    fingerprint="fp-parent",
                    collected_at=datetime.now(timezone.utc),
                )
            )
            session.add_all([
                RelatedJob(
                    parent_job_id=parent_job_id,
                    related_external_id="101",
                    related_url="https://www.linkedin.com/jobs/view/101/",
                    canonical_related_job_url="https://www.linkedin.com/jobs/view/101/",
                    title="Related Pending",
                    company="Company Y",
                    promotion_status="pending",
                ),
                RelatedJob(
                    parent_job_id=parent_job_id,
                    related_external_id="102",
                    related_url="https://www.linkedin.com/jobs/view/102/",
                    canonical_related_job_url="https://www.linkedin.com/jobs/view/102/",
                    title="Related Promoted",
                    company="Company Z",
                    promotion_status="promoted",
                ),
            ])
            await session.commit()

    import asyncio
    asyncio.run(init_data())

    async def override_get_db_session():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        client = TestClient(app)
        response = client.get(
            "/related-jobs?promotion_status=pending",
            headers={"X-API-Key": "changeme"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert len(payload["items"]) == 1
        assert payload["items"][0]["promotion_status"] == "pending"
        assert payload["items"][0]["related_external_id"] == "101"
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())