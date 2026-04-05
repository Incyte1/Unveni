import type {
  MarketClock,
  SignalAlert,
  SignalFocus,
  SignalPortfolioState
} from "../lib/contracts";

interface WhatShouldIDoNowPanelProps {
  alerts: SignalAlert[];
  error: string | null;
  focus: SignalFocus | null;
  isLoading: boolean;
  marketClock: MarketClock | null;
  marketDataQuality: "provider" | "fallback" | "mixed" | null;
  marketDataSource: string | null;
  portfolio: SignalPortfolioState | null;
  onSelectSignal: (symbol: string) => void;
}

export function WhatShouldIDoNowPanel({
  alerts,
  error,
  focus,
  isLoading,
  marketClock,
  marketDataQuality,
  marketDataSource,
  portfolio,
  onSelectSignal
}: WhatShouldIDoNowPanelProps) {
  const focusSymbol = focus?.symbol ?? null;
  const marketLabel = marketClock
    ? `Market ${marketClock.is_open ? "open" : "closed"} - ${marketClock.phase.replace("_", " ")} - next ${marketClock.is_open ? marketClock.next_close : marketClock.next_open}`
    : "Market status unavailable";

  return (
    <section className="panel reveal focusPanel">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">What should I do now?</p>
          <h2>Immediate decision</h2>
        </div>
        {focus?.action ? (
          <span className={`actionBadge is${focus.action}`}>
            {focus.action.toLowerCase().replace("_", " ")}
          </span>
        ) : null}
      </div>

      {isLoading ? (
        <div className="stateBlock">
          <strong>Preparing guidance...</strong>
          <p>The decision engine is ranking what matters right now.</p>
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="stateBlock isError">
          <strong>Guidance unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {!isLoading && !error && focus ? (
        <>
          <div className="signalBoardMeta">
            <span>
              Data {marketDataSource ?? "unknown"} ({marketDataQuality ?? "unknown"})
            </span>
            <span>{marketLabel}</span>
          </div>

          <div className="focusHero">
            <div>
              <strong>{focus.headline}</strong>
              <p>{focus.summary}</p>
            </div>
            {focusSymbol ? (
              <button
                className="secondaryButton"
                type="button"
                onClick={() => onSelectSignal(focusSymbol)}
              >
                Open {focusSymbol}
              </button>
            ) : null}
          </div>

          <div className="focusSteps">
            {focus.next_steps.map((step) => (
              <div
                key={step}
                className="infoCard"
              >
                <strong>Next step</strong>
                <p>{step}</p>
              </div>
            ))}
          </div>

          <div className="metricCards focusMetrics">
            <div className="metricCard">
              <span>Exposure used</span>
              <strong>{portfolio?.gross_exposure_pct.toFixed(1) ?? "0.0"}%</strong>
            </div>
            <div className="metricCard">
              <span>Exposure left</span>
              <strong>{portfolio?.available_exposure_pct.toFixed(1) ?? "0.0"}%</strong>
            </div>
            <div className="metricCard">
              <span>Risk utilization</span>
              <strong>{portfolio?.risk_utilization_pct.toFixed(1) ?? "0.0"}%</strong>
            </div>
            <div className="metricCard">
              <span>Day P&amp;L</span>
              <strong className={(portfolio?.daily_pnl ?? 0) >= 0 ? "positive" : "negative"}>
                {portfolio?.daily_pnl_pct.toFixed(2) ?? "0.00"}%
              </strong>
            </div>
          </div>

          {focus.warnings.length > 0 ? (
            <>
              <div className="sectionSubheader">
                <p className="eyebrow">Warnings</p>
              </div>
              <div className="warningList">
                {focus.warnings.map((warning) => (
                  <div
                    key={warning}
                    className="warningItem"
                  >
                    <span className="warningTag iscaution">watch</span>
                    <div>
                      <strong>Manage the setup tightly</strong>
                      <p>{warning}</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : null}

          {alerts.length > 0 ? (
            <>
              <div className="sectionSubheader">
                <p className="eyebrow">Internal alerts</p>
              </div>
              <div className="stackList">
                {alerts.slice(0, 3).map((alert) => (
                  <article
                    key={alert.id}
                    className="alertCard"
                  >
                    <div className="watchlistCardTop">
                      <div>
                        <strong>{alert.title}</strong>
                        <p className="sectionMeta">{alert.message}</p>
                      </div>
                      <span className={`warningTag is${alert.severity}`}>{alert.severity}</span>
                    </div>
                  </article>
                ))}
              </div>
            </>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
