import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.config import get_settings


AI_LOG_PATH = Path("data/ai_responses_log.json")


def save_ai_response(
    prompt: str,
    response: str,
    chat_url: str | None = None,
    provider: str = "unknown",
    success: bool = True,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
    log_path: Path | None = None,
) -> dict[str, Any]:
    """Salva prompt e resposta da automação de IA em JSON lines."""
    target_path = log_path or AI_LOG_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "prompt": prompt,
        "response": response,
        "chat_url": chat_url,
        "success": success,
        "metadata": metadata or {},
        "error": error,
    }

    with open(target_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(data, ensure_ascii=False) + "\n")

    return data


def save_raw_html(html: str, source: str, canonical_url: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    month_dir = now.strftime("%Y-%m")
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    job_key = hashlib.sha1(canonical_url.encode("utf-8")).hexdigest()[:12]

    path = Path(settings.raw_html_dir) / source / month_dir / job_key
    path.mkdir(parents=True, exist_ok=True)

    filepath = path / f"{ts}.html.gz"
    with gzip.open(filepath, "wt", encoding="utf-8") as f:
        f.write(html)
    return str(filepath)
