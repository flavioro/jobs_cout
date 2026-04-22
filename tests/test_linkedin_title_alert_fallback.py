import pytest
from src.adapters.linkedin.extractor import LinkedInExtractor
from src.core.contracts import RawPage

def make_raw_page_mock(html_content):
    """Auxiliar para criar um objeto RawPage para o teste."""
    return RawPage(
        url="https://www.linkedin.com/jobs/view/12345",
        final_url="https://www.linkedin.com/jobs/view/12345",
        html=html_content,
        title="LinkedIn", # Título da aba genérico para forçar a busca no HTML
        apply_url=None
    )

@pytest.mark.parametrize("html_snippet, expected_title", [
    # Cenário 1: Título com vírgula vindo do Alerta de Vagas (Seu caso real)
    ("""
    <div>
        <h2>Ative um alerta para vagas semelhantes</h2>
        <div><p>Desenvolvedor Python, Brasil</p></div>
    </div>
    """, "Desenvolvedor Python"),
    
    # Cenário 2: Outra variação de cargo e cidade
    ("""
    <div>
        <h2>Ative um alerta para vagas semelhantes</h2>
        <p>Engenheiro de Software, Rio de Janeiro, Brasil</p>
    </div>
    """, "Engenheiro de Software"),
])
def test_extract_title_from_alert_fallback(html_snippet, expected_title):
    """
    Testa se o extrator consegue capturar o título da seção de 'Alerta de Vagas'
    quando os seletores de H1 falham, e se ele limpa corretamente a localização.
    """
    extractor = LinkedInExtractor()
    raw_page = make_raw_page_mock(html_snippet)
    
    payload = extractor.extract(raw_page)
    
    # Validações
    assert payload.fields["title"] == expected_title
    assert "location_not_found" in payload.extraction_notes or payload.fields["location_raw"] is None