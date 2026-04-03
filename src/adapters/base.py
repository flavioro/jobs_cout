from abc import ABC, abstractmethod

from src.core.contracts import RawJobPayload, RawPage
from src.schemas.jobs import IngestUrlRequest, JobRecordSchema


class BaseAdapter(ABC):
    source_name: str

    @abstractmethod
    async def fetch(self, url: str) -> RawPage:
        raise NotImplementedError

    @abstractmethod
    def extract(self, raw_page: RawPage) -> RawJobPayload:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, payload: RawJobPayload, request: IngestUrlRequest) -> JobRecordSchema:
        raise NotImplementedError
