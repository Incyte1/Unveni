import type { MarketOverviewResponse } from "../lib/contracts";

interface MarketOverviewPanelProps {
  data: MarketOverviewResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function MarketOverviewPanel({
  data,
  isLoading,
  error
}: MarketOverviewPanelProps) {
  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Market overview</p>
          <h2>Regime pulse</h2>
        </div>
        <p className="sectionMeta">
          Provider-backed intraday market context where available, with explicit development fallback otherwise.
        </p>
      </div>

      {isLoading ? (
        <div className="stateBlock">
          <strong>Loading market overview...</strong>
          <p>The dashboard is waiting for the latest regime and event summary.</p>
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="stateBlock isError">
          <strong>Market overview unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {!isLoading && !error && data ? (
        <>
          <div className="signalBoardMeta">
            <span>Source {data.source}</span>
            <span>
              Market {data.clock.is_open ? "open" : "closed"} - {data.clock.phase.replace("_", " ")} - next{" "}
              {data.clock.is_open ? data.clock.next_close : data.clock.next_open}
            </span>
          </div>

          <p className="detailCopy">{data.regime.summary}</p>

          <div className="detailGrid">
            <div>
              <span className="detailLabel">Volatility regime</span>
              <strong>{data.regime.volatility_regime}</strong>
            </div>
            <div>
              <span className="detailLabel">Breadth regime</span>
              <strong>{data.regime.breadth_regime}</strong>
            </div>
          </div>

          <div className="overviewBenchmarks">
            {data.benchmarks.map((benchmark) => (
              <div
                key={benchmark.symbol}
                className="metricCard"
              >
                <span>{benchmark.symbol}</span>
                <strong className={benchmark.move_pct >= 0 ? "positive mono" : "negative mono"}>
                  {benchmark.move_pct >= 0 ? "+" : ""}
                  {benchmark.move_pct.toFixed(1)}%
                </strong>
                <p className="sectionMeta">{benchmark.note}</p>
              </div>
            ))}
          </div>

          <div className="sectionSubheader">
            <p className="eyebrow">Highlights</p>
          </div>
          <ul className="plainList">
            {data.highlights.map((highlight) => (
              <li key={highlight}>{highlight}</li>
            ))}
          </ul>

          <div className="sectionSubheader">
            <p className="eyebrow">Upcoming events</p>
          </div>
          <div className="eventList">
            {data.upcoming_events.map((event) => (
              <div
                key={`${event.label}-${event.scheduled_at}`}
                className="eventItem"
              >
                <div>
                  <strong>{event.label}</strong>
                  <p>{event.scheduled_at}</p>
                </div>
                <span className={`warningTag is${event.impact}`}>{event.impact}</span>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
