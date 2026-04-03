from src.adapters.linkedin.extractor import LinkedInExtractor
from src.core.contracts import RawPage


def test_extractor_can_fallback_to_tab_title_when_dom_title_is_missing():
    html = """
    <html>
      <body>
        <a href="https://www.linkedin.com/company/acme/">Acme</a>
        <div data-testid="expandable-text-box">Python, APIs e integrações.</div>
      </body>
    </html>
    """

    raw_page = RawPage(
        url="https://www.linkedin.com/jobs/view/123/",
        final_url="https://www.linkedin.com/jobs/view/123/",
        html=html,
        title="Backend Python Developer | Acme | LinkedIn",
    )

    payload = LinkedInExtractor().extract(raw_page)
    assert payload.fields["title"] == "Backend Python Developer"
    assert payload.fields["company"] == "Acme"
    assert payload.fields["description_text"] == "Python, APIs e integrações."


def test_extractor_strips_company_and_work_model_from_title_fallback():
    html = """
    <html>
      <body>
        <a href="https://www.linkedin.com/company/rd-station/">RD Station</a>
        <div data-testid="expandable-text-box">Atuação em backend Python.</div>
      </body>
    </html>
    """

    raw_page = RawPage(
        url="https://www.linkedin.com/jobs/view/999/",
        final_url="https://www.linkedin.com/jobs/view/999/",
        html=html,
        title="Engenharia de Software Backend Pleno - Python | RD Station (Remoto) | RD Station | LinkedIn",
    )

    payload = LinkedInExtractor().extract(raw_page)
    assert payload.fields["title"] == "Engenharia de Software Backend Pleno - Python"
    assert payload.fields["company"] == "RD Station"
    assert payload.fields["workplace_type"] == "remote"
