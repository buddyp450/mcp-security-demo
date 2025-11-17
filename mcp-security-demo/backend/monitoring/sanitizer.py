from __future__ import annotations

from typing import Any, Dict


class OutputSanitizer:
    def sanitize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        clean_payload = {k: v for k, v in payload.items() if k in {"insights", "recommendation"}}
        clean_payload.setdefault("meta", {"sanitized": True})
        return clean_payload
