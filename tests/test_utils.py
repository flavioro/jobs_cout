from src.core.enums import AvailabilityStatus, ClosedReason
from src.utils.text import (
    clean_location_raw,
    detect_availability,
    map_seniority,
    map_workplace_type,
    nullify_placeholder,
    sanitize_title,
    find_blocking_keyword
)
from src.utils.url import build_canonical_url


def test_build_canonical_url_strips_tracking_params():
    url = "https://www.linkedin.com/jobs/view/9876543210/?refId=abc&trackingId=xyz"
    assert build_canonical_url(url) == "https://www.linkedin.com/jobs/view/9876543210/"


def test_map_seniority_detects_mid():
    result = map_seniority("Desenvolvedor Python Pleno")
    assert result is not None
    assert result.value == "mid"


def test_clean_location_raw_removes_relative_time_and_candidate_counts():
    value = "São Paulo, São Paulo, Brasil · há 1 dia · 25 pessoas clicaram em Candidate-se"
    assert clean_location_raw(value) == "São Paulo, São Paulo, Brasil"


def test_workplace_type_can_come_from_description_even_when_location_is_generic():
    result = map_workplace_type(None, None, "Brasil", None, "Horário: trabalho 100% remoto.")
    assert result is not None
    assert result.value == "remote"


def test_detect_availability_for_closed_job():
    status, reason = detect_availability("Esta vaga não aceita mais candidaturas")
    assert status == AvailabilityStatus.CLOSED
    assert reason == ClosedReason.DOES_NOT_ACCEPT_APPLICATIONS


def test_sanitize_title_removes_company_and_work_model_suffix():
    result = sanitize_title("Engenharia de Software Backend Pleno - Python | RD Station (Remoto)", "RD Station")
    assert result == "Engenharia de Software Backend Pleno - Python"


def test_nullify_placeholder_string_returns_none():
    assert nullify_placeholder("string") is None


def test_map_seniority_does_not_treat_internas_as_intern():
    result = map_seniority("Analista Desenvolvedor Junior", "Colaborar com equipes internas")
    assert result is not None
    assert result.value == "junior"


def test_clean_location_raw_removes_shared_and_click_noise():
    value = "Brasil · Compartilhou há 1 dia · Mais de 100 pessoas clicaram em Candidate-se"
    assert clean_location_raw(value) == "Brasil"


# --- NOVOS TESTES: BLOCKLIST (PORTEIRO) ---

def test_find_blocking_keyword_matches_exact_word():
    blocklist = ["mkt", "marketing", "vendas"]
    assert find_blocking_keyword("Analista de Vendas", blocklist) == "vendas"
    assert find_blocking_keyword("Diretor de MKT (Remoto)", blocklist) == "mkt"
    assert find_blocking_keyword("MARKETING DIGITAL", blocklist) == "marketing"


def test_find_blocking_keyword_ignores_partial_matches():
    blocklist = ["mkt", "vendas"]
    # "mktsystem" contém "mkt", mas não é a palavra exata, então não deve bloquear
    assert find_blocking_keyword("Desenvolvedor Mktsystem", blocklist) is None
    # "vendashub" contém "vendas", mas é uma palavra composta
    assert find_blocking_keyword("Engenheiro Vendashub", blocklist) is None


def test_find_blocking_keyword_returns_none_for_clean_titles():
    blocklist = ["mkt", "marketing", "vendas"]
    assert find_blocking_keyword("Backend Python Developer", blocklist) is None
    assert find_blocking_keyword("Engenheiro de Software", blocklist) is None