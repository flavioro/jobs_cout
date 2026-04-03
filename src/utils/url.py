import re
from urllib.parse import parse_qs, urlparse, urlunparse


def is_supported_linkedin_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    if parsed.netloc not in {"www.linkedin.com", "linkedin.com"}:
        return False
    return "/jobs/view/" in parsed.path


def extract_linkedin_job_id(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return None

    match = re.search(r"/jobs/view/(\d+)", parsed.path)
    if match:
        return match.group(1)

    query = parse_qs(parsed.query)
    current_job_id = query.get("currentJobId", [None])[0]
    if current_job_id:
        return current_job_id

    return None


def build_canonical_url(url: str) -> str:
    job_id = extract_linkedin_job_id(url)
    if job_id:
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    parsed = urlparse(url.strip())
    return urlunparse(parsed._replace(query="", fragment=""))


def build_canonical_related_job_url(related_external_id: str | None = None, related_url: str | None = None) -> str | None:
    job_id = related_external_id or extract_linkedin_job_id(related_url)
    if job_id:
        return f"https://www.linkedin.com/jobs/view/{job_id}/"

    if not related_url:
        return None

    parsed = urlparse(related_url.strip())
    return urlunparse(parsed._replace(query="", fragment=""))
