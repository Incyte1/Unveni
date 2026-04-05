import type { IntradayScorecardResponse } from "../lib/contracts";

interface IntradayScorecardPanelProps {
  data: IntradayScorecardResponse | null;
  error: string | null;
  isLoading: boolean;
  onSelectSignal: (symbol: string) => void;
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD"
});

function outcomeLabel(outcome: "target_hit" | "stop_hit" | "exit_signal" | "open" | "no_resolution") {
  return outcome.replace(/_/g, " ");
}

export function IntradayScorecardPanel({
  data,
  error,
  isLoading,
  onSelectSignal
}: IntradayScorecardPanelProps) {
  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Today&apos;s scorecard</p>
          <h2>How did the engine do?</h2>
        </div>
        <p className="sectionMeta">Lightweight same-day review of triggered setups, alerts, and first outcomes.</p>
      </div>

      {isLoading ? (
        <div className="stateBlock">
          <strong>Building scorecard...</strong>
          <p>The backend is summarizing today&apos;s triggered setups and alert trail.</p>
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="stateBlock isError">
          <strong>Scorecard unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {!isLoading && !error && data ? (
        <>
          <div className="metricCards">
            <div className="metricCard">
              <span>Symbols tracked</span>
              <strong>{data.symbols_with_snapshots}</strong>
            </div>
            <div className="metricCard">
              <span>Triggered setups</span>
              <strong>{data.actionable_signals}</strong>
            </div>
            <div className="metricCard">
              <span>Alerts fired</span>
              <strong>{data.alerts_fired}</strong>
            </div>
            <div className="metricCard">
              <span>Fallback alerts</span>
              <strong>{data.fallback_alerts}</strong>
            </div>
          </div>

          {data.items.length === 0 ? (
            <div className="stateBlock">
              <strong>No triggered setups yet.</strong>
              <p>The scorecard fills once the persisted state layer records a new actionable setup or confirmation.</p>
            </div>
          ) : (
            <div className="stackList">
              {data.items.slice(0, 6).map((item) => (
                <button
                  key={`${item.symbol}-${item.triggered_at}`}
                  type="button"
                  className="signalCardButton"
                  onClick={() => onSelectSignal(item.symbol)}
                >
                  <article className="signalCard scorecardCard">
                    <div className="signalCardHeader">
                      <div>
                        <strong>{item.symbol}</strong>
                        <p className="sectionMeta">
                          {item.setup_type.replace(/_/g, " ")} - {new Date(item.triggered_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                        </p>
                      </div>
                      <span className={`actionBadge is${item.action}`}>{item.action.toLowerCase().replace(/_/g, " ")}</span>
                    </div>

                    <div className="signalLevelGrid">
                      <div>
                        <span className="detailLabel">Outcome</span>
                        <strong>{outcomeLabel(item.outcome)}</strong>
                      </div>
                      <div>
                        <span className="detailLabel">Entry</span>
                        <strong>{item.entry_price ? currencyFormatter.format(item.entry_price) : "--"}</strong>
                      </div>
                      <div>
                        <span className="detailLabel">Stop</span>
                        <strong>{item.stop_loss ? currencyFormatter.format(item.stop_loss) : "--"}</strong>
                      </div>
                      <div>
                        <span className="detailLabel">Target</span>
                        <strong>{item.take_profit1 ? currencyFormatter.format(item.take_profit1) : "--"}</strong>
                      </div>
                    </div>

                    <div className="signalStatRow">
                      <span className="tag mono">{item.alert_count} alerts</span>
                      <span className="tag mono">{item.market_phase.replace(/_/g, " ")}</span>
                      <span className="tag mono">{item.market_data_quality}</span>
                    </div>

                    <div className="signalReasonList">
                      {item.notes.map((note) => (
                        <p key={`${item.symbol}-${item.triggered_at}-${note}`}>{note}</p>
                      ))}
                    </div>
                  </article>
                </button>
              ))}
            </div>
          )}

          {data.setup_stats.length > 0 ? (
            <>
              <div className="sectionSubheader">
                <p className="eyebrow">Setup stats</p>
              </div>
              <div className="stackList">
                {data.setup_stats.map((stat) => (
                  <div
                    key={stat.setup_type}
                    className="infoCard"
                  >
                    <div className="watchlistCardTop">
                      <strong>{stat.setup_type.replace(/_/g, " ")}</strong>
                      <span className="tag mono">{stat.win_rate_pct.toFixed(1)}% win rate</span>
                    </div>
                    <p>
                      {stat.total} triggers, {stat.target_hits} target hits, {stat.stop_hits} stop hits, {stat.exit_signals} exit signals, {stat.open} still open.
                    </p>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
