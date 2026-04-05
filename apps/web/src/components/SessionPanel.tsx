import { useState, type FormEvent } from "react";
import type { SessionResponse } from "../lib/contracts";

interface SessionPanelProps {
  actionError: string | null;
  isLoading: boolean;
  isSaving: boolean;
  onStartSession: (payload: {
    access_token?: string | null;
    display_name?: string | null;
    handle: string;
  }) => Promise<boolean>;
  session: SessionResponse | null;
  sessionError: string | null;
}

function sessionHint(session: SessionResponse | null) {
  if (!session) {
    return "Start a server-owned session to unlock watchlist persistence and paper trading.";
  }

  if (session.session_strategy === "development") {
    return "Local development mode mints a real HTTP-only session cookie without an external identity provider.";
  }

  if (session.session_strategy === "local-token") {
    return "This server requires the shared bootstrap token before it will mint a local session.";
  }

  return "Session creation is disabled until an external identity provider is connected.";
}

export function SessionPanel({
  actionError,
  isLoading,
  isSaving,
  onStartSession,
  session,
  sessionError
}: SessionPanelProps) {
  const [handle, setHandle] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [accessToken, setAccessToken] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const started = await onStartSession({
      handle,
      display_name: displayName.trim() ? displayName : null,
      access_token: accessToken.trim() ? accessToken : null
    });

    if (started) {
      setAccessToken("");
    }
  }

  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Session boundary</p>
          <h2>Sign in</h2>
        </div>
        <p className="sectionMeta">Watchlist persistence and paper trading now require a real server-owned session.</p>
      </div>

      {isLoading ? (
        <div className="stateBlock">
          <strong>Loading session state...</strong>
          <p>The dashboard is checking for an active server session.</p>
        </div>
      ) : null}

      {!isLoading ? <p className="detailCopy">{sessionHint(session)}</p> : null}

      {sessionError ? (
        <div className="stateBlock isError">
          <strong>Session lookup failed.</strong>
          <p>{sessionError}</p>
        </div>
      ) : null}

      {actionError ? (
        <div className="stateBlock isError">
          <strong>Session creation failed.</strong>
          <p>{actionError}</p>
        </div>
      ) : null}

      <form
        className="panelForm"
        onSubmit={handleSubmit}
      >
        <div className="formGrid">
          <label>
            <span className="detailLabel">Handle</span>
            <input
              className="searchInput"
              value={handle}
              onChange={(event) => setHandle(event.target.value.toLowerCase())}
              placeholder="operator-1"
              maxLength={32}
            />
          </label>
          <label>
            <span className="detailLabel">Display name</span>
            <input
              className="searchInput"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Operator One"
              maxLength={60}
            />
          </label>
          <label>
            <span className="detailLabel">Access token</span>
            <input
              className="searchInput"
              type="password"
              value={accessToken}
              onChange={(event) => setAccessToken(event.target.value)}
              placeholder={session?.requires_local_token ? "Required by this server" : "Optional in local dev"}
              maxLength={128}
            />
          </label>
        </div>
        <div className="actionRow">
          <button
            className="primaryButton"
            type="submit"
            disabled={isSaving || session?.session_strategy === "external"}
          >
            {isSaving ? "Starting..." : "Start session"}
          </button>
        </div>
      </form>
    </section>
  );
}
