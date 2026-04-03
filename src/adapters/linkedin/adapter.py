from src.adapters.base import BaseAdapter
from src.adapters.linkedin.extractor import LinkedInExtractor
from src.adapters.linkedin.fetcher import fetch_linkedin_page
from src.core.contracts import RawJobPayload, RawPage
from src.core.normalization import normalize_linkedin_payload
from src.schemas.jobs import IngestUrlRequest, JobRecordSchema


class LinkedInAdapter(BaseAdapter):
    source_name = "linkedin"

    def __init__(self) -> None:
        self.extractor = LinkedInExtractor()

    async def fetch(self, url: str) -> RawPage:
        return await fetch_linkedin_page(url)

    def extract(self, raw_page: RawPage) -> RawJobPayload:
        return self.extractor.extract(raw_page)

    def normalize(self, payload: RawJobPayload, request: IngestUrlRequest) -> JobRecordSchema:
        return normalize_linkedin_payload(payload, request)
