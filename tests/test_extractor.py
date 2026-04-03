from pathlib import Path

from src.adapters.linkedin.extractor import LinkedInExtractor
from src.core.contracts import RawPage


def test_extracts_title_company_and_description():
    html = (Path(__file__).parent / "fixtures" / "linkedin_job_v1.html").read_text(encoding="utf-8")
    raw_page = RawPage(
        url="https://www.linkedin.com/jobs/view/1",
        final_url="https://www.linkedin.com/jobs/view/1",
        html=html,
        title="LinkedIn Job",
    )
    payload = LinkedInExtractor().extract(raw_page)
    assert payload.fields["title"] == "Backend Python Developer"
    assert payload.fields["company"] == "Acme"
    assert "Python" in payload.fields["description_text"]
