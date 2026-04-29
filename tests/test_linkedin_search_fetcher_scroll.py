from src.adapters.linkedin.search_fetcher import LinkedInSearchSession


def test_incremental_card_merge_preserves_link_only_cards_and_prefers_richer_payload():
    session = LinkedInSearchSession()
    seen = {}

    link_only = {
        "linkedin_job_id": "123",
        "linkedin_job_url": "https://www.linkedin.com/jobs/view/123/",
        "title": "Backend Python",
        "company": None,
        "location_raw": None,
        "card_text_raw": "Backend Python",
        "availability_status": "unknown",
    }
    richer = {
        "linkedin_job_id": "123",
        "linkedin_job_url": "https://www.linkedin.com/jobs/view/123/",
        "title": "Backend Python",
        "company": "ACME",
        "location_raw": "Brasil (Remoto)",
        "card_text_raw": "Backend Python ACME Brasil (Remoto)",
        "availability_status": "unknown",
    }

    session._merge_cards_into_seen(seen, [link_only])
    assert seen["id:123"]["company"] is None

    session._merge_cards_into_seen(seen, [richer])
    assert len(seen) == 1
    assert seen["id:123"]["company"] == "ACME"
    assert seen["id:123"]["location_raw"] == "Brasil (Remoto)"


def test_incremental_card_merge_keeps_closed_status_when_later_detected():
    session = LinkedInSearchSession()
    seen = {}

    open_payload = {
        "linkedin_job_id": "456",
        "linkedin_job_url": "https://www.linkedin.com/jobs/view/456/",
        "title": "Chatbot Developer",
        "company": "Simbium.com",
        "location_raw": "São Paulo (Híbrido)",
        "availability_status": "unknown",
    }
    closed_payload = {
        "linkedin_job_id": "456",
        "linkedin_job_url": "https://www.linkedin.com/jobs/view/456/",
        "title": "Chatbot Developer",
        "company": "Simbium.com",
        "location_raw": "São Paulo (Híbrido)",
        "availability_status": "closed",
        "availability_reason": "expired_or_no_longer_accepting_applications",
    }

    session._merge_cards_into_seen(seen, [open_payload])
    session._merge_cards_into_seen(seen, [closed_payload])

    assert seen["id:456"]["availability_status"] == "closed"
    assert seen["id:456"]["availability_reason"] == "expired_or_no_longer_accepting_applications"


def test_detail_completion_reuses_ingest_url_extractor_for_individual_job_page():
    session = LinkedInSearchSession()
    html = """
    <html>
      <head><title>Python Engineer - Work from home | Nortal | LinkedIn</title></head>
      <body>
        <main>
          <section class="job-details-jobs-unified-top-card">
            <div class="job-details-jobs-unified-top-card__job-title"><h1>Python Engineer - Work from home</h1></div>
            <div class="job-details-jobs-unified-top-card__company-name"><a>Nortal</a></div>
            <div class="job-details-jobs-unified-top-card__primary-description-container">São Paulo e Região · há 3 horas · Remoto</div>
          </section>
          <div class="jobs-description__content">Descrição da vaga Python.</div>
        </main>
      </body>
    </html>
    """

    detail = session._extract_detail_with_ingest_extractor(
        job_url="https://www.linkedin.com/jobs/view/123/",
        final_url="https://www.linkedin.com/jobs/view/123/",
        html=html,
        page_title="Python Engineer - Work from home | Nortal | LinkedIn",
        detail_text="Nortal Python Engineer - Work from home São Paulo e Região Remoto Tempo integral",
    )

    assert detail["title"] == "Python Engineer - Work from home"
    assert detail["company"] == "Nortal"
    assert detail["location_raw"]
    assert "São Paulo" in detail["location_raw"]
    assert detail["detail_completion_source"] == "ingest_extractor"


def test_merge_detail_marks_completion_source_from_ingest_extractor():
    session = LinkedInSearchSession()
    card = {
        "linkedin_job_id": "123",
        "linkedin_job_url": "https://www.linkedin.com/jobs/view/123/",
        "title": "Python Engineer - Work from home",
        "company": None,
        "location_raw": None,
        "availability_status": "unknown",
    }
    detail = {
        "title": "Python Engineer - Work from home",
        "company": "Nortal",
        "location_raw": "São Paulo e Região",
        "detail_completed": True,
        "detail_url_opened": True,
        "detail_completion_source": "ingest_extractor",
    }

    merged = session._merge_detail(card, detail)

    assert merged["company"] == "Nortal"
    assert merged["location_raw"] == "São Paulo e Região"
    assert merged["detail_completed"] is True
    assert merged["detail_completion_source"] == "ingest_extractor"
