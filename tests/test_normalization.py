from src.core.normalization import normalize_linkedin_payload
from src.schemas.jobs import IngestUrlRequest


class DummyPayload:
    def __init__(self, fields: dict):
        self.fields = fields


def test_normalization_uses_extracted_workplace_type_and_cleans_location():
    payload = DummyPayload(
        {
            "title": "Engenharia de Software Backend Pleno - Python",
            "company": "RD Station",
            "location_raw": "Brasil · há 1 dia · Mais de 100 candidaturas",
            "description_text": "Trabalho 100% remoto.",
            "is_easy_apply": True,
            "apply_url": None,
            "workplace_type": "remote",
            "availability_status": "open",
            "closed_reason": None,
            "related_jobs": [],
        }
    )
    request = IngestUrlRequest(url="https://www.linkedin.com/jobs/view/4392892148/")
    record = normalize_linkedin_payload(payload, request)
    assert record.location_raw == "Brasil"
    assert record.workplace_type.value == "remote"


def test_normalization_keeps_closed_status_separate_from_technical_status():
    payload = DummyPayload(
        {
            "title": "f582 DESENVOLVEDOR III",
            "company": "Extreme Digital Solutions - EDS",
            "location_raw": "Brasil · Compartilhou há 1 dia · Mais de 100 pessoas clicaram em Candidate-se",
            "description_text": "Atuação remota em Node.js",
            "is_easy_apply": False,
            "apply_url": None,
            "workplace_type": "remote",
            "availability_status": "closed",
            "closed_reason": "does_not_accept_applications",
            "related_jobs": [],
        }
    )
    request = IngestUrlRequest(url="https://www.linkedin.com/jobs/view/4383830220/")
    record = normalize_linkedin_payload(payload, request)
    assert record.status.value == "success"
    assert record.availability_status.value == "closed"
    assert record.closed_reason.value == "does_not_accept_applications"


def test_normalization_junior_hint_wins_over_internal_text_noise():
    payload = DummyPayload(
        {
            "title": "Analista Desenvolvedor Junior",
            "company": "Banco Industrial do Brasil S/A",
            "location_raw": "São Paulo, São Paulo, Brasil",
            "description_text": "Colaborar com equipes internas e fornecedores externos.",
            "is_easy_apply": False,
            "apply_url": "https://example.com",
            "workplace_type": "onsite",
            "availability_status": "open",
            "closed_reason": None,
            "related_jobs": [],
        }
    )
    request = IngestUrlRequest(url="https://www.linkedin.com/jobs/view/4396458716/")
    record = normalize_linkedin_payload(payload, request)
    assert record.seniority_normalized.value == "junior"
