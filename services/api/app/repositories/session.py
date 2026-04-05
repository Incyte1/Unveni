from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from uuid import uuid4

from app.db import DatabaseSession


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionRepository:
    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    def upsert_local_user(
        self,
        handle: str,
        display_name: str,
        entitlement: str,
        execution_mode: str
    ) -> Mapping[str, object]:
        now = utc_now_iso()
        self.session.execute(
            """
            INSERT INTO users (
                id,
                handle,
                display_name,
                auth_provider,
                provider_subject,
                entitlement,
                execution_mode,
                is_active,
                created_at,
                updated_at
            )
            VALUES (
                :id,
                :handle,
                :display_name,
                'local',
                :provider_subject,
                :entitlement,
                :execution_mode,
                1,
                :created_at,
                :updated_at
            )
            ON CONFLICT (auth_provider, provider_subject) DO UPDATE SET
                handle = excluded.handle,
                display_name = excluded.display_name,
                entitlement = excluded.entitlement,
                execution_mode = excluded.execution_mode,
                updated_at = excluded.updated_at
            """,
            {
                "id": str(uuid4()),
                "handle": handle,
                "display_name": display_name,
                "provider_subject": handle,
                "entitlement": entitlement,
                "execution_mode": execution_mode,
                "created_at": now,
                "updated_at": now
            }
        )
        user = self.session.fetchone(
            """
            SELECT
                id,
                handle,
                display_name,
                auth_provider,
                provider_subject,
                entitlement,
                execution_mode,
                is_active,
                created_at,
                updated_at
            FROM users
            WHERE auth_provider = 'local' AND provider_subject = :provider_subject
            """,
            {"provider_subject": handle}
        )
        if user is None:  # pragma: no cover - guarded by upsert
            raise RuntimeError("user_upsert_failed")
        return user

    def create_session(
        self,
        user_id: str,
        token_hash: str,
        expires_at: str,
        ip_address: str | None,
        user_agent: str | None
    ) -> Mapping[str, object]:
        session_id = str(uuid4())
        now = utc_now_iso()
        self.session.execute(
            """
            INSERT INTO sessions (
                id,
                user_id,
                token_hash,
                created_at,
                expires_at,
                last_seen_at,
                revoked_at,
                ip_address,
                user_agent
            )
            VALUES (
                :id,
                :user_id,
                :token_hash,
                :created_at,
                :expires_at,
                :last_seen_at,
                NULL,
                :ip_address,
                :user_agent
            )
            """,
            {
                "id": session_id,
                "user_id": user_id,
                "token_hash": token_hash,
                "created_at": now,
                "expires_at": expires_at,
                "last_seen_at": now,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )
        session_row = self.session.fetchone(
            """
            SELECT
                sessions.id AS session_id,
                sessions.user_id,
                sessions.expires_at,
                users.handle,
                users.display_name,
                users.entitlement,
                users.execution_mode,
                users.auth_provider
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.id = :session_id
            """,
            {"session_id": session_id}
        )
        if session_row is None:  # pragma: no cover - guarded by insert
            raise RuntimeError("session_create_failed")
        return session_row

    def find_session_by_token_hash(self, token_hash: str) -> Mapping[str, object] | None:
        return self.session.fetchone(
            """
            SELECT
                sessions.id AS session_id,
                sessions.user_id,
                sessions.expires_at,
                sessions.revoked_at,
                users.handle,
                users.display_name,
                users.entitlement,
                users.execution_mode,
                users.auth_provider,
                users.is_active
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = :token_hash
            """,
            {"token_hash": token_hash}
        )

    def touch_session(self, session_id: str) -> None:
        self.session.execute(
            """
            UPDATE sessions
            SET last_seen_at = :last_seen_at
            WHERE id = :session_id
            """,
            {
                "session_id": session_id,
                "last_seen_at": utc_now_iso()
            }
        )

    def revoke_session(self, session_id: str) -> None:
        self.session.execute(
            """
            UPDATE sessions
            SET revoked_at = :revoked_at
            WHERE id = :session_id
            """,
            {
                "session_id": session_id,
                "revoked_at": utc_now_iso()
            }
        )
