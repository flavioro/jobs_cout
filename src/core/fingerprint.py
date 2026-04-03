import hashlib
import json


def build_fingerprint(record: dict) -> str:
    relevant = {
        "canonical_url": record.get("canonical_url", ""),
        "title": (record.get("title") or "").strip().lower(),
        "company": (record.get("company") or "").strip().lower(),
        "description_text": (record.get("description_text") or "").strip(),
        "workplace_type": (record.get("workplace_type") or "").strip().lower(),
    }
    payload = json.dumps(relevant, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
