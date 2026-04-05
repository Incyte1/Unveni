import type { SignalsResponse, TradingSignalRecord } from "../lib/contracts";

interface ActionableSignalsPanelProps {
  data: SignalsResponse | null;
  error: string | null;
  isLoading: boolean;
  items: TradingSignalRecord[];
  onSelect: (symbol: string) => void;
  selectedSymbol: string;
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD"
});

function actionLabel(action: TradingSignalRecord["action"]) {
  return action.toLowerCase().replace("_", " ");
}

function entryStateLabel(entryState: TradingSignalRecord["entry_state"]) {
  switch (entryState) {
    case "enter_now":
      return "entry now";
    case "wait_for_confirmation":
      return "wait";
    case "manage_position":
      return "manage";
    case "stand_aside":
      return "stand aside";
    default:
      return entryState;
  }
}

function formatEntry(signal: TradingSignalRecord) {
  if (signal.entry_zone) {
    return signal.entry_zone;
  }

  if (signal.entry_price) {
    return currencyFormatter.format(signal.entry_price);
  }

  return "--";
}

export function ActionableSignalsPanel({
  data,
  error,
  isLoading,
  items,
  onSelect,
  selectedSymbol
}: ActionableSignalsPanelProps) {
  const actionableCount = data?.items.filter((item) => item.is_actionable).length ?? 0;

  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Decision engine</p>
          <h2>Top actionable signals</h2>
        </div>
        <p className="sectionMeta">
          Deterministic intraday signal output after opening range, VWAP, momentum, and risk checks.
        </p>
      </div>

      {isLoading ? (
        <div className="stateBlock">
          <strong>Loading signals...</strong>
          <p>The decision engine is scoring symbols against the current market and portfolio state.</p>
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="stateBlock isError">
          <strong>Signals unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {!isLoading && !error && items.length === 0 ? (
        <div className="stateBlock">
          <strong>No symbols match the current search.</strong>
          <p>Clear the search or add more names to the watchlist to widen the signal set.</p>
        </div>
      ) : null}

      {!isLoading && !error && items.length > 0 ? (
        <>
          <div className="signalBoardMeta">
            <span>{actionableCount} actionable decisions</span>
            <span>{data?.portfolio.open_positions ?? 0} live paper positions tracked</span>
            <span>
              Market data {data?.market_data_source ?? "unknown"} ({data?.market_data_quality ?? "unknown"})
            </span>
          </div>

          <div className="signalCardGrid">
            {items.slice(0, 6).map((signal) => (
              <button
                key={signal.symbol}
                type="button"
                className={
                  signal.symbol === selectedSymbol
                    ? "signalCardButton isSelected"
                    : "signalCardButton"
                }
                onClick={() => onSelect(signal.symbol)}
              >
                <article className="signalCard">
                  <div className="signalCardHeader">
                    <div>
                      <strong>{signal.symbol}</strong>
                      <p className="sectionMeta">
                        {signal.strategy_type} - {signal.timeframe}
                      </p>
                    </div>
                    <span className={`actionBadge is${signal.action}`}>
                      {actionLabel(signal.action)}
                    </span>
                  </div>

                  <p className="detailCopy">{signal.thesis}</p>

                  <div className="signalStatRow">
                    <span className="tag mono">Confidence {signal.confidence}</span>
                    <span className="tag mono">Score {signal.score}</span>
                    <span className="tag mono">{entryStateLabel(signal.entry_state)}</span>
                    <span className="tag mono">{signal.market_data_source}</span>
                    <span className="tag mono">{signal.market_data_quality}</span>
                    {signal.has_position && signal.current_position ? (
                      <span className="tag mono">
                        Held {signal.current_position.quantity} sh
                      </span>
                    ) : null}
                  </div>

                  <div className="signalLevelGrid">
                    <div>
                      <span className="detailLabel">Setup</span>
                      <strong>{signal.strategy_type}</strong>
                    </div>
                    <div>
                      <span className="detailLabel">Entry</span>
                      <strong>{formatEntry(signal)}</strong>
                    </div>
                    <div>
                      <span className="detailLabel">Stop</span>
                      <strong>{signal.stop_loss ? currencyFormatter.format(signal.stop_loss) : "--"}</strong>
                    </div>
                    <div>
                      <span className="detailLabel">Trigger</span>
                      <strong>
                        {signal.trigger_price ? currencyFormatter.format(signal.trigger_price) : "--"}
                      </strong>
                    </div>
                    <div>
                      <span className="detailLabel">Target 1</span>
                      <strong>
                        {signal.take_profit1 ? currencyFormatter.format(signal.take_profit1) : "--"}
                      </strong>
                    </div>
                    <div>
                      <span className="detailLabel">Status</span>
                      <strong>{entryStateLabel(signal.entry_state)}</strong>
                    </div>
                    <div>
                      <span className="detailLabel">Size</span>
                      <strong>{signal.position_size_pct.toFixed(1)}%</strong>
                    </div>
                  </div>

                  <div className="signalReasonList">
                    {signal.reasons.slice(0, 2).map((reason) => (
                      <p key={reason}>{reason}</p>
                    ))}
                  </div>

                  {signal.warnings[0] ? (
                    <div className="signalInlineWarning">
                      <span className="warningTag iscaution">watch</span>
                      <p>{signal.warnings[0]}</p>
                    </div>
                  ) : null}
                </article>
              </button>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
