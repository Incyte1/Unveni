import type { SignalAlert } from "../lib/contracts";

interface SignalAlertsPanelProps {
  error: string | null;
  isLoading: boolean;
  items: SignalAlert[];
  onAcknowledge: (alertId: string) => Promise<unknown>;
  onMarkRead: (alertId: string) => Promise<unknown>;
  onSelectSymbol: (symbol: string) => void;
  selectedWindow: number;
  onSelectWindow: (minutes: number) => void;
}

const timeFormatter = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit"
});

const WINDOW_OPTIONS = [
  { label: "15m", minutes: 15 },
  { label: "30m", minutes: 30 },
  { label: "60m", minutes: 60 },
  { label: "4h", minutes: 240 }
];

export function SignalAlertsPanel({
  error,
  isLoading,
  items,
  onAcknowledge,
  onMarkRead,
  onSelectSymbol,
  selectedWindow,
  onSelectWindow
}: SignalAlertsPanelProps) {
  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Signal changes</p>
          <h2>What changed recently?</h2>
        </div>
        <p className="sectionMeta">Persisted alerts from signal transitions, risk events, and degraded data quality.</p>
      </div>

      <div className="filterList">
        {WINDOW_OPTIONS.map((option) => (
          <button
            key={option.minutes}
            className={option.minutes === selectedWindow ? "filterChip isSelected" : "filterChip"}
            type="button"
            onClick={() => onSelectWindow(option.minutes)}
          >
            Last {option.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="stateBlock">
          <strong>Loading recent changes...</strong>
          <p>The backend is comparing fresh intraday snapshots against prior state.</p>
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="stateBlock isError">
          <strong>Alert feed unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {!isLoading && !error && items.length === 0 ? (
        <div className="stateBlock">
          <strong>No meaningful changes yet.</strong>
          <p>The engine has not recorded a new setup, downgrade, exit, stop, target, or fallback warning in this window.</p>
        </div>
      ) : null}

      {!isLoading && !error && items.length > 0 ? (
        <div className="stackList">
          {items.map((alert) => (
            <article
              key={alert.id}
              className="alertCard"
            >
              <div className="watchlistCardTop">
                <div>
                  <strong>{alert.title}</strong>
                  <p className="sectionMeta">{alert.message}</p>
                </div>
                <div className="alertMeta">
                  <span className={`warningTag is${alert.severity}`}>{alert.severity}</span>
                  <span className={`warningTag is${alert.status === "acknowledged" ? "low" : alert.status === "read" ? "info" : "medium"}`}>
                    {alert.status}
                  </span>
                </div>
              </div>

              <div className="signalBoardMeta">
                <span>{alert.symbol ?? "Portfolio-wide"}</span>
                <span>{timeFormatter.format(new Date(alert.timestamp))}</span>
                <span>{alert.data_quality ?? "unknown"} data</span>
              </div>

              {alert.change_types.length > 0 ? (
                <div className="signalStatRow">
                  {alert.change_types.map((changeType) => (
                    <span
                      key={`${alert.id}-${changeType}`}
                      className="tag mono"
                    >
                      {changeType.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              ) : null}

              <div className="actionRow">
                {alert.symbol ? (
                  <button
                    className="secondaryButton"
                    type="button"
                    onClick={() => {
                      onSelectSymbol(alert.symbol as string);
                      void onMarkRead(alert.id);
                    }}
                  >
                    Open {alert.symbol}
                  </button>
                ) : null}
                {alert.status !== "acknowledged" ? (
                  <button
                    className="secondaryButton"
                    type="button"
                    onClick={() => void onAcknowledge(alert.id)}
                  >
                    Acknowledge
                  </button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
