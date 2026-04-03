from pathlib import Path
import sys
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "linkedin"

CASES = {
    "4383830220": {
        "job_id": "4383830220",
        "title": "f582 DESENVOLVEDOR III",
        "company": "Extreme Digital Solutions - EDS",
        "location_exact": "Brasil",
        "description_contains": "O que você fará?",
        "easy_apply": False,
        "availability_status": "closed",
        "closed_reason": "does_not_accept_applications",
        "workplace_type": "remote",
        "related_jobs_min": 10,
    },
    "4396458716": {
        "job_id": "4396458716",
        "title": "Analista Desenvolvedor Junior",
        "company": "Banco Industrial do Brasil S/A",
        "location_exact": "São Paulo, São Paulo, Brasil",
        "description_contains": "Venha fazer parte do nosso Time Tech",
        "easy_apply": False,
        "availability_status": "open",
        "closed_reason": None,
        "workplace_type": "onsite",
        "related_jobs_min": 5,
    },
    "4392892148": {
        "job_id": "4392892148",
        "title": "Engenharia de Software Backend Pleno - Python",
        "company": "RD Station",
        "location_exact": "Brasil",
        "description_contains": "Quer fazer parte de um time que cria oportunidades",
        "easy_apply": True,
        "availability_status": "open",
        "closed_reason": None,
        "workplace_type": "remote",
        "related_jobs_min": 10,
    },
    "4396673137": {
        "job_id": "4396673137",
        "title": "Desenvolvedor(a) de Software Júnior",
        "company": "LINA",
        "location_exact": "Brasil",
        "description_contains": "A Lina Open X é uma fintech",
        "easy_apply": False,
        "availability_status": "open",
        "closed_reason": None,
        "workplace_type": "remote",
        "related_jobs_min": 10,
    },
    "4392808079": {
        "job_id": "4392808079",
        "title": "Desenvolvedor(a) Python / Golang Pleno",
        "company": "INDT - Instituto de Desenvolvimento Tecnológico",
        "location_exact": "São Paulo, São Paulo, Brasil",
        "description_contains": "Sobre Nós Desde 2001, o INDT é um instituto de tecnologia",
        "easy_apply": False,
        "availability_status": "open",
        "closed_reason": None,
        "workplace_type": "hybrid",
        "related_jobs_min": 10,
    },
}


def _load_case(job_id: str) -> dict:
    prefix = FIXTURES_DIR / f"linkedin_{job_id}"
    return {
        "html": prefix.with_suffix('.html').read_text(encoding='utf-8'),
        "page_title": prefix.with_suffix('.title.txt').read_text(encoding='utf-8').strip(),
        "final_url": prefix.with_suffix('.url.txt').read_text(encoding='utf-8').strip(),
        **CASES[job_id],
    }


@pytest.fixture(params=list(CASES.keys()), ids=list(CASES.keys()))
def linkedin_case(request):
    return _load_case(request.param)
