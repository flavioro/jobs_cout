from pathlib import Path

from src.adapters.linkedin.search_extractor import LinkedInSearchExtractor


def test_linkedin_search_extractor_extracts_job_cards():
    html = Path("tests/fixtures/linkedin_search/linkedin_python_search.html").read_text(encoding="utf-8")
    extractor = LinkedInSearchExtractor()

    items = extractor.extract(html, source_search_url="https://www.linkedin.com/jobs/search/?keywords=python")

    assert len(items) >= 20
    first = items[0]
    assert first.linkedin_job_id == "4243924693"
    assert first.linkedin_job_url == "https://www.linkedin.com/jobs/view/4243924693/"
    assert first.title == "Desenvolvedor(a) IA"
    assert first.company == "Keyrus"
    assert first.location_raw == "São Paulo, São Paulo, Brasil (Presencial)"
    assert first.workplace_type == "onsite"
    assert first.extraction_status == "complete"
    assert first.card_text_raw
    assert first.source_search_url == "https://www.linkedin.com/jobs/search/?keywords=python"


def test_linkedin_search_extractor_classifies_partial_and_closed_cards():
    html = """
    <ul>
      <li data-occludable-job-id="111"><a href="/jobs/view/111/" class="job-card-container__link">Python Developer</a></li>
      <li data-occludable-job-id="222">
        <a href="/jobs/view/222/" class="job-card-container__link"><strong>Chatbot Developer</strong></a>
        <div class="job-card-container__primary-description">Simbium.com</div>
        <span class="job-card-container__metadata-item">Brasil (Remoto)</span>
        <span>Expirado</span>
      </li>
    </ul>
    """
    items = LinkedInSearchExtractor().extract(html)
    partial = items[0]
    closed = items[1]

    assert partial.extraction_status == "partial"
    assert partial.missing_fields == ["company", "location_raw"]
    assert closed.extraction_status == "closed"
    assert closed.availability_status == "closed"
    assert closed.availability_reason == "expired_or_no_longer_accepting_applications"
    assert "Expirado" in closed.card_text_raw


def test_linkedin_search_extractor_builds_card_from_browser_payload_completed_by_detail():
    payload = {
        "linkedin_job_url": "https://www.linkedin.com/jobs/view/333/?trackingId=abc",
        "title": "Pessoa Desenvolvedora Python",
        "company": "FCamara",
        "location_raw": "Brasil (Remoto)",
        "card_text_raw": "link parcial",
        "detail_text": "Pessoa Desenvolvedora Python FCamara Brasil (Remoto)",
        "detail_completed": True,
        "detail_url_opened": True,
    }

    card = LinkedInSearchExtractor().from_browser_payload(payload)

    assert card is not None
    assert card.linkedin_job_id == "333"
    assert card.linkedin_job_url == "https://www.linkedin.com/jobs/view/333/"
    assert card.extraction_status == "complete"
    assert card.detail_completed is True
    assert card.detail_url_opened is True
    assert card.card_text_raw == "link parcial"


def test_linkedin_search_extractor_closed_detection_from_browser_text_wins_over_unknown_status():
    payload = {
        "linkedin_job_id": "444",
        "linkedin_job_url": "https://www.linkedin.com/jobs/view/444/",
        "title": "Chatbot Developer",
        "company": "Simbium.com",
        "location_raw": "São Paulo, São Paulo, Brasil (Híbrido)",
        "availability_status": "unknown",
        "card_text_raw": "Chatbot Developer Simbium.com São Paulo, São Paulo, Brasil (Híbrido) Expirado",
    }

    card = LinkedInSearchExtractor().from_browser_payload(payload)

    assert card is not None
    assert card.availability_status == "closed"
    assert card.extraction_status == "closed"
