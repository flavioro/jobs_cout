from src.adapters.linkedin.extractor import LinkedInExtractor
from src.core.contracts import RawPage


def make_raw_page(case: dict) -> RawPage:
    return RawPage(
        url=case["final_url"],
        final_url=case["final_url"],
        html=case["html"],
        title=case["page_title"],
    )


def test_related_jobs_are_deduplicated_and_have_parent_safe_fields(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    canonical_urls = [item["canonical_related_job_url"] for item in related_jobs if item.get("canonical_related_job_url")]
    assert len(canonical_urls) == len(set(canonical_urls))
    assert all(item["title"] for item in related_jobs)


def test_related_jobs_capture_posted_text_or_candidate_signal(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    assert any(item.get("posted_text_raw") or item.get("candidate_signal_raw") for item in related_jobs)


def test_related_job_company_is_not_equal_to_title_for_verified_cards(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    verified_cards = [item for item in related_jobs if item.get("is_verified")]
    assert verified_cards
    assert all((item.get("company") or "").casefold() != (item.get("title") or "").casefold() for item in verified_cards if item.get("company"))


def test_related_job_location_is_not_company_name(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    checked = [item for item in related_jobs if item.get("company") and item.get("location_raw")]
    assert checked
    assert all((item["company"].casefold() != item["location_raw"].casefold()) for item in checked)


def test_related_job_canonical_url_from_related_external_id(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    with_external_id = [item for item in related_jobs if item.get("related_external_id")]
    assert with_external_id
    for item in with_external_id:
        expected = f"https://www.linkedin.com/jobs/view/{item['related_external_id']}/"
        assert item["canonical_related_job_url"] == expected


def test_related_job_workplace_type_from_parenthesized_location(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    candidates = [item for item in related_jobs if item.get("location_raw") and "(" in item["location_raw"] and ")" in item["location_raw"]]
    assert candidates
    assert any(item.get("workplace_type") in {"remote", "hybrid", "onsite"} for item in candidates)


def test_related_job_verified_cards_preserve_is_verified_true(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    assert any(item.get("is_verified") is True for item in related_jobs)


def test_related_job_posted_text_raw_is_preserved(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    assert any((item.get("posted_text_raw") or "").startswith("Anunciada há") for item in related_jobs)


def test_related_job_candidate_signal_raw_is_preserved(linkedin_case):
    payload = LinkedInExtractor().extract(make_raw_page(linkedin_case))
    related_jobs = payload.fields["related_jobs"]

    assert any(item.get("candidate_signal_raw") == "Avaliando candidaturas" for item in related_jobs)


def test_related_job_swaps_company_and_location_when_company_looks_like_location():
    extractor = LinkedInExtractor()
    company, location_raw = extractor._sanitize_related_company_and_location(
        "Engenheiro de Software JR | .NET",
        ["São Paulo, SP (Híbrido)", "Evertec Brasil"],
    )

    assert company == "Evertec Brasil"
    assert location_raw == "São Paulo, SP (Híbrido)"


def test_related_job_company_fallback_skips_title_duplicate_for_verified_cards():
    extractor = LinkedInExtractor()
    company, location_raw = extractor._sanitize_related_company_and_location(
        "Desenvolvedor Python (Vaga verificada)",
        ["Desenvolvedor Python", "Exadel"],
    )

    assert company == "Exadel"
    assert location_raw is None


def test_related_job_location_can_be_restored_from_swapped_verified_card_layout():
    extractor = LinkedInExtractor()
    company, location_raw = extractor._sanitize_related_company_and_location(
        "Desenvolvedor Fullstack Python - Remoto (Vaga verificada)",
        ["Getronics", "Brasil (Remoto)"],
    )

    assert company == "Getronics"
    assert location_raw == "Brasil (Remoto)"


def test_related_job_company_is_not_location_text():
    extractor = LinkedInExtractor()
    company, _ = extractor._sanitize_related_company_and_location(
        "Backend Engineer",
        ["Brasil (Remoto)", "Crossing Hurdles"],
    )

    assert company == "Crossing Hurdles"


def test_related_job_location_raw_is_cleaned_after_swap():
    extractor = LinkedInExtractor()
    company, location_raw = extractor._sanitize_related_company_and_location(
        "Backend Engineer",
        ["São Paulo, SP (Híbrido)", "ACME Ltda"],
    )

    assert company == "ACME Ltda"
    assert location_raw == "São Paulo, SP (Híbrido)"
