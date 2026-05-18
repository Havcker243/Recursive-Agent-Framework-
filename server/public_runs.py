import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class PublicRunStore:
    def __init__(self) -> None:
        self.url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.key)

    def _headers(self, *, json_body: bool = False) -> Dict[str, str]:
        headers = {
            "apikey": self.key,
        }
        # Supabase's new secret keys are opaque rather than JWTs, so the
        # apikey header is the portable auth mechanism across both key styles.
        if self.key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {self.key}"
        if json_body:
            headers["Content-Type"] = "application/json"
            headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        return headers

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        params = {
            "select": "id,goal,provider,model,status,created_at,published_at,event_count",
            "order": "published_at.desc",
            "limit": str(limit),
        }
        response = httpx.get(
            f"{self.url}/rest/v1/public_runs",
            headers=self._headers(),
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        params = {
            "select": "id,goal,provider,model,status,result,events,created_at,published_at,event_count",
            "id": f"eq.{run_id}",
            "limit": "1",
        }
        response = httpx.get(
            f"{self.url}/rest/v1/public_runs",
            headers=self._headers(),
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        rows = response.json()
        return rows[0] if rows else None

    def publish_run(self, run: Any) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Supabase public-run storage is not configured.")
        payload = {
            "id": run.run_id,
            "goal": run.goal,
            "provider": run.provider,
            "model": run.model,
            "status": run.status,
            "result": run.result,
            "events": run.events,
            "created_at": run.started_at,
            "event_count": len(run.events),
        }
        response = httpx.post(
            f"{self.url}/rest/v1/public_runs",
            headers=self._headers(json_body=True),
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        rows = response.json()
        return rows[0] if rows else payload

    def publish_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Supabase public-run storage is not configured.")
        payload = {
            "id": snapshot["id"],
            "goal": snapshot["goal"],
            "provider": snapshot["provider"],
            "model": snapshot.get("model"),
            "status": snapshot["status"],
            "result": snapshot.get("result"),
            "events": snapshot.get("events", []),
            "created_at": snapshot["created_at"],
            "event_count": len(snapshot.get("events", [])),
        }
        response = httpx.post(
            f"{self.url}/rest/v1/public_runs",
            headers=self._headers(json_body=True),
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        rows = response.json()
        return rows[0] if rows else payload
