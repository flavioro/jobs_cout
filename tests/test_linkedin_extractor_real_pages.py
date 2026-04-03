from bs4 import BeautifulSoup

from src.adapters.linkedin.extractor import LinkedInExtractor
from src.core.contracts import RawPage


def make_raw_page(case: dict) -> RawPage:
    return RawPage(
        url=case["final_url"],
        final_url=case["final_url"],
        html=case["html"],
        title=case["page_title"],
    )


def test_real_linkedin_pages_have_expected_signals(linkedin_case):
    soup = BeautifulSoup(linkedin_case["html"], "lxml")
    assert soup.select_one("[data-testid='expandable-text-box']") is not None
    assert soup.select_one("a[href*='/company/']") is not None


def test_real_linkedin_pages_do_not_depend_on_h1(linkedin_case):
    soup = BeautifulSoup(linkedin_case["html"], "lxml")
    assert not soup.find_all("h1")


def test_extractor_extracts_core_fields_from_real_linkedin_pages(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))

    assert payload.source == "linkedin"
    assert payload.source_url == linkedin_case["final_url"]
    assert payload.fields["title"] == linkedin_case["title"]
    assert payload.fields["company"] == linkedin_case["company"]
    assert payload.fields["location_raw"] == linkedin_case["location_exact"]
    assert linkedin_case["description_contains"] in (payload.fields["description_text"] or "")
    assert payload.fields["is_easy_apply"] is linkedin_case["easy_apply"]
    assert payload.fields["availability_status"] == linkedin_case["availability_status"]
    assert payload.fields["closed_reason"] == linkedin_case["closed_reason"]
    assert payload.fields["workplace_type"] == linkedin_case["workplace_type"]


def test_extractor_collects_related_jobs_from_real_pages(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    assert len(related_jobs) >= linkedin_case["related_jobs_min"]
    first = related_jobs[0]
    assert first["title"]
    assert first["company"]
    assert first["related_url"]


def test_extractor_does_not_flag_missing_core_fields_for_real_pages(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    assert "title_not_found" not in payload.extraction_notes
    assert "company_not_found" not in payload.extraction_notes
    assert "description_not_found" not in payload.extraction_notes
