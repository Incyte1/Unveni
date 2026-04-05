import type { SignalHistoryResponse, TradingSignalRecord } from "../lib/contracts";
import { ChartContainer } from "./chart/ChartContainer";

interface SignalInspectorProps {
  history: SignalHistoryResponse | null;
  historyError: string | null;
  isHistoryLoading: boolean;
  signal: TradingSignalRecord | null;
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD"
});

export function SignalInspector({
  history,
  historyError,
  isHistoryLoading,
  signal
}: SignalInspectorProps) {
  if (!signal) {
    return (
      <section className="panel reveal">
        <div className="sectionHeader">
          <div>
            <p className="eyebrow">Signal detail</p>
            <h2>No signal selected</h2>
          </div>
        </div>
        <p className="detailCopy">
          Select a signal to inspect the action, risk plan, reasons, and current position context.
        </p>
      </section>
    );
  }

  return (
    <section className="panel reveal inspector">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Signal detail</p>
          <h2>{signal.symbol}</h2>
        </div>
        <div className="signalHeaderMeta">
          <span className={`actionBadge is${signal.action}`}>{signal.action.toLowerCase()}</span>
          <span className="scorePill mono">{signal.score}</span>
        </div>
      </div>

      <p className="detailCopy">{signal.thesis}</p>

      <div className="detailGrid">
        <div>
          <span className="detailLabel">Confidence</span>
          <strong className="mono">{signal.confidence}</strong>
        </div>
        <div>
          <span className="detailLabel">Setup</span>
          <strong>{signal.strategy_type}</strong>
        </div>
        <div>
          <span className="detailLabel">Timeframe</span>
          <strong>{signal.timeframe}</strong>
        </div>
        <div>
          <span className="detailLabel">Entry state</span>
          <strong>{signal.entry_state.replace(/_/g, " ")}</strong>
        </div>
        <div>
          <span className="detailLabel">Size</span>
          <strong>{signal.position_size_pct.toFixed(1)}%</strong>
        </div>
        <div>
          <span className="detailLabel">Data source</span>
          <strong>{signal.market_data_source}</strong>
        </div>
        <div>
          <span className="detailLabel">Session phase</span>
          <strong>{signal.intraday_features.session_phase.replace(/_/g, " ")}</strong>
        </div>
        <div>
          <span className="detailLabel">Data quality</span>
          <strong>{signal.market_data_quality}</strong>
        </div>
      </div>

      {signal.current_position ? (
        <div className="infoCard">
          <strong>Already in the book</strong>
          <p>
            {signal.current_position.quantity} shares at{" "}
            {currencyFormatter.format(signal.current_position.average_cost)} average cost.
            Market value is {currencyFormatter.format(signal.current_position.market_value)} and
            total P&amp;L is {currencyFormatter.format(signal.current_position.total_pnl)}.
          </p>
        </div>
      ) : null}

      <div className="signalLevelGrid isInspector">
        <div>
          <span className="detailLabel">Trigger</span>
          <strong>{signal.trigger_price ? currencyFormatter.format(signal.trigger_price) : "--"}</strong>
        </div>
        <div>
          <span className="detailLabel">Entry</span>
          <strong>
            {signal.entry_zone ??
              (signal.entry_price ? currencyFormatter.format(signal.entry_price) : "--")}
          </strong>
        </div>
        <div>
          <span className="detailLabel">Stop loss</span>
          <strong>{signal.stop_loss ? currencyFormatter.format(signal.stop_loss) : "--"}</strong>
        </div>
        <div>
          <span className="detailLabel">Target 1</span>
          <strong>
            {signal.take_profit1 ? currencyFormatter.format(signal.take_profit1) : "--"}
          </strong>
        </div>
        <div>
          <span className="detailLabel">Target 2</span>
          <strong>
            {signal.take_profit2 ? currencyFormatter.format(signal.take_profit2) : "--"}
          </strong>
        </div>
        <div>
          <span className="detailLabel">Risk / reward</span>
          <strong>{signal.risk_reward ? `${signal.risk_reward.toFixed(2)}R` : "--"}</strong>
        </div>
        <div>
          <span className="detailLabel">Invalidation</span>
          <strong>{signal.invalidation}</strong>
        </div>
      </div>

      <div className="sectionSubheader">
        <p className="eyebrow">Signal history</p>
      </div>
      {isHistoryLoading ? (
        <div className="stateBlock">
          <strong>Loading state changes...</strong>
          <p>The inspector is fetching recent persisted snapshots for this symbol.</p>
        </div>
      ) : null}
      {!isHistoryLoading && historyError ? (
        <div className="stateBlock isError">
          <strong>History unavailable.</strong>
          <p>{historyError}</p>
        </div>
      ) : null}
      {!isHistoryLoading && !historyError && (history?.items.length ?? 0) > 0 ? (
        <div className="stackList">
          {history?.items.slice(0, 6).map((snapshot) => (
            <div
              key={snapshot.snapshot_id}
              className="infoCard"
            >
              <div className="watchlistCardTop">
                <div>
                  <strong>
                    {new Date(snapshot.snapshot_at).toLocaleTimeString([], {
                      hour: "numeric",
                      minute: "2-digit"
                    })}{" "}
                    - {snapshot.strategy_type}
                  </strong>
                  <p>
                    {snapshot.action} with confidence {snapshot.confidence} during{" "}
                    {snapshot.market_phase.replace(/_/g, " ")}.
                  </p>
                </div>
                <span className={`actionBadge is${snapshot.action}`}>
                  {snapshot.action.toLowerCase().replace(/_/g, " ")}
                </span>
              </div>
              {snapshot.transition?.headline ? (
                <p className="detailCopy">{snapshot.transition.headline}</p>
              ) : null}
              {snapshot.transition?.changes.length ? (
                <div className="signalReasonList">
                  {snapshot.transition.changes.slice(0, 3).map((change) => (
                    <p key={`${snapshot.snapshot_id}-${change.type}`}>
                      {change.summary}: {change.detail}
                    </p>
                  ))}
                </div>
              ) : (
                <p className="detailCopy">No material change was detected against the prior snapshot.</p>
              )}
            </div>
          ))}
        </div>
      ) : null}
      {!isHistoryLoading && !historyError && signal && (history?.items.length ?? 0) === 0 ? (
        <div className="stateBlock">
          <strong>No persisted history yet.</strong>
          <p>This symbol has not accumulated tracked snapshots yet for the signed-in session.</p>
        </div>
      ) : null}

      <div className="detailGrid">
        <div>
          <span className="detailLabel">Opening range</span>
          <strong>
            {signal.intraday_features.opening_range_low && signal.intraday_features.opening_range_high
              ? `${currencyFormatter.format(signal.intraday_features.opening_range_low)} - ${currencyFormatter.format(signal.intraday_features.opening_range_high)}`
              : "--"}
          </strong>
        </div>
        <div>
          <span className="detailLabel">VWAP</span>
          <strong>
            {signal.intraday_features.vwap
              ? currencyFormatter.format(signal.intraday_features.vwap)
              : "--"}
          </strong>
        </div>
        <div>
          <span className="detailLabel">Rel. volume</span>
          <strong>{signal.intraday_features.relative_volume.toFixed(2)}x</strong>
        </div>
        <div>
          <span className="detailLabel">5m momentum</span>
          <strong>{signal.intraday_features.momentum_5m_pct.toFixed(2)}%</strong>
        </div>
        <div>
          <span className="detailLabel">15m momentum</span>
          <strong>{signal.intraday_features.momentum_15m_pct.toFixed(2)}%</strong>
        </div>
        <div>
          <span className="detailLabel">Breakout state</span>
          <strong>{signal.intraday_features.breakout_state.replace(/_/g, " ")}</strong>
        </div>
      </div>

      <ChartContainer
        symbol={signal.symbol}
        title="Underlying chart"
        notes={[
          signal.next_watch,
          signal.trailing_stop?.detail ?? "Trailing stop is inactive until price earns it."
        ]}
      />

      <div className="sectionSubheader">
        <p className="eyebrow">Why this call</p>
      </div>
      <div className="stackList">
        {signal.reasons.map((reason) => (
          <div
            key={reason}
            className="infoCard"
          >
            <strong>Reason</strong>
            <p>{reason}</p>
          </div>
        ))}
      </div>

      {signal.warnings.length > 0 ? (
        <>
          <div className="sectionSubheader">
            <p className="eyebrow">Warnings</p>
          </div>
          <div className="warningList">
            {signal.warnings.map((warning) => (
              <div
                key={warning}
                className="warningItem"
              >
                <span className="warningTag iscaution">watch</span>
                <div>
                  <strong>Risk note</strong>
                  <p>{warning}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}

      <div className="sectionSubheader">
        <p className="eyebrow">Entry rules</p>
      </div>
      <div className="stackList">
        {signal.entry_rules.map((rule) => (
          <div
            key={`${signal.symbol}-${rule.label}`}
            className="infoCard"
          >
            <div className="watchlistCardTop">
              <strong>{rule.label}</strong>
              <span className={`warningTag is${rule.status === "blocked" ? "risk" : rule.status === "triggered" ? "high" : rule.status === "met" ? "low" : "medium"}`}>
                {rule.status}
              </span>
            </div>
            <p>{rule.detail}</p>
          </div>
        ))}
      </div>

      <div className="sectionSubheader">
        <p className="eyebrow">Exit rules</p>
      </div>
      <div className="stackList">
        {signal.exit_rules.map((rule) => (
          <div
            key={`${signal.symbol}-exit-${rule.label}`}
            className="infoCard"
          >
            <div className="watchlistCardTop">
              <strong>{rule.label}</strong>
              <span className={`warningTag is${rule.status === "triggered" ? "high" : rule.status === "met" ? "low" : rule.status === "blocked" ? "risk" : "medium"}`}>
                {rule.status}
              </span>
            </div>
            <p>{rule.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
