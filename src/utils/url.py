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


def build_canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    match = re.search(r"/jobs/view/(\d+)", parsed.path)
    if match:
        job_id = match.group(1)
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    return urlunparse(parsed._replace(query="", fragment=""))


def build_canonical_related_job_url(related_external_id: str | None = None, related_url: str | None = None) -> str | None:
    if related_external_id:
        return f"https://www.linkedin.com/jobs/view/{related_external_id}/"

    if not related_url:
        return None

    parsed = urlparse(related_url.strip())
    query = parse_qs(parsed.query)
    current_job_id = query.get("currentJobId", [None])[0]
    if current_job_id:
        return f"https://www.linkedin.com/jobs/view/{current_job_id}/"

    match = re.search(r"/jobs/view/(\d+)", parsed.path)
    if match:
        return f"https://www.linkedin.com/jobs/view/{match.group(1)}/"

    return urlunparse(parsed._replace(query="", fragment=""))
