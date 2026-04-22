import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import get_settings

def save_ai_response(prompt: str, response: str, chat_url: str = None):
    """
    Salva o prompt e a resposta da IA em um arquivo JSON de log.
    """
    # Garante que a pasta data existe
    log_path = Path("data/ai_responses_log.json")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "response": response,
        "chat_url": chat_url
    }

    # "a" abre o arquivo em modo append (adiciona ao final sem apagar o anterior)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

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
