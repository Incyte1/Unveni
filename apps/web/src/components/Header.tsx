import type { SessionResponse } from "../lib/contracts";
import {
  formatEntitlement,
  formatExecutionMode,
  formatSessionLabel
} from "../lib/session";

interface HeaderProps {
  actionableCount: number;
  signalCount: number;
  session: SessionResponse | null;
  sessionError: string | null;
  isSessionLoading: boolean;
  isSessionSaving: boolean;
  onLogout: () => Promise<boolean>;
  refreshedAt: string | null;
}

export function Header({
  actionableCount,
  signalCount,
  session,
  sessionError,
  isSessionLoading,
  isSessionSaving,
  onLogout,
  refreshedAt
}: HeaderProps) {
  const refreshTime = new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit"
  }).format(refreshedAt ? new Date(refreshedAt) : new Date());

  const modeLabel = session ? formatExecutionMode(session.execution_mode) : "Paper mode";
  const entitlementLabel = session
    ? formatEntitlement(session.entitlement)
    : "Delayed OPRA-safe analytics";
  const sessionLabel = sessionError
    ? "Session unavailable"
    : isSessionLoading
      ? "Loading session"
      : formatSessionLabel(session);

  return (
    <header className="topbar panel reveal">
      <div>
        <p className="eyebrow">Unveni</p>
        <h1>Personal trading signal engine</h1>
      </div>
      <div className="statusRail">
        <div className="statusChip">
          <span className="statusDot statusDotPaper" />
          {modeLabel}
        </div>
        <div className="statusChip">
          <span className="statusDot statusDotData" />
          {entitlementLabel}
        </div>
        <div className="statusChip">{actionableCount} live decisions</div>
        <div className="statusChip">{signalCount} symbols scored</div>
        <div className="statusChip">{sessionLabel}</div>
        <div className="statusChip">Refreshed {refreshTime}</div>
        {session?.is_authenticated ? (
          <button
            className="secondaryButton"
            type="button"
            onClick={() => void onLogout()}
            disabled={isSessionSaving}
          >
            {isSessionSaving ? "Signing out..." : "Log out"}
          </button>
        ) : null}
      </div>
    </header>
  );
}
