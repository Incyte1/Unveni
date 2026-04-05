from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from app.db import DatabaseSession


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditRepository:
    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    def record_event(
        self,
        event_type: str,
        user_id: str | None = None,
        session_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, object] | None = None
    ) -> None:
        self.session.execute(
            """
            INSERT INTO audit_events (
                id,
                event_type,
                user_id,
                session_id,
                entity_type,
                entity_id,
                payload_json,
                created_at
            )
            VALUES (
                :id,
                :event_type,
                :user_id,
                :session_id,
                :entity_type,
                :entity_id,
                :payload_json,
                :created_at
            )
            """,
            {
                "id": str(uuid4()),
                "event_type": event_type,
                "user_id": user_id,
                "session_id": session_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "payload_json": json.dumps(payload or {}),
                "created_at": utc_now_iso()
            }
        )
