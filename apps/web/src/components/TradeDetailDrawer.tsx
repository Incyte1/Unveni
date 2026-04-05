import { useEffect, useState } from "react";
import { getTradeDetail, toErrorMessage } from "../lib/api";
import type {
  OpportunityRecord,
  TradeDetailResponse
} from "../lib/contracts";
import { ChartContainer } from "./chart/ChartContainer";

interface TradeDetailDrawerProps {
  opportunity: OpportunityRecord;
}

function buildPayoffPoints(values: number[]) {
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 320;
      const y = 100 - ((value + 2) / 4.5) * 100;
      return `${x},${y}`;
    })
    .join(" ");
}

export function TradeDetailDrawer({ opportunity }: TradeDetailDrawerProps) {
  const [detail, setDetail] = useState<TradeDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    setIsLoading(true);
    setError(null);

    getTradeDetail(opportunity.id, controller.signal)
      .then((response) => {
        setDetail(response);
        setIsLoading(false);
      })
      .catch((requestError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setError(toErrorMessage(requestError));
        setIsLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [opportunity.id]);

  const activeTrade = detail ?? {
    id: opportunity.id,
    symbol: opportunity.symbol,
    structure: opportunity.structure,
    thesis: opportunity.thesis,
    score: opportunity.score,
    dte: opportunity.dte,
    iv_rank: 0,
    spread_bps: opportunity.spread_bps,
    expected_return: opportunity.expected_return,
    max_loss: opportunity.max_loss,
    expected_shortfall: opportunity.expected_shortfall,
    greeks: opportunity.greeks,
    payoff: [],
    scenario: [],
    notes: []
  };

  return (
    <section className="panel reveal inspector">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Selected trade</p>
          <h2>
            {activeTrade.symbol} {activeTrade.structure}
          </h2>
        </div>
        <span className="scorePill mono">{activeTrade.score}</span>
      </div>

      <p className="detailCopy">{activeTrade.thesis}</p>

      <div className="detailGrid">
        <div>
          <span className="detailLabel">DTE</span>
          <strong className="mono">{activeTrade.dte}</strong>
        </div>
        <div>
          <span className="detailLabel">Max loss</span>
          <strong className="mono">${activeTrade.max_loss.toFixed(2)}</strong>
        </div>
        <div>
          <span className="detailLabel">IV rank</span>
          <strong className="mono">{activeTrade.iv_rank || "--"}</strong>
        </div>
        <div>
          <span className="detailLabel">Spread</span>
          <strong className="mono">{activeTrade.spread_bps} bps</strong>
        </div>
      </div>

      <ChartContainer
        symbol={activeTrade.symbol}
        title="Underlying chart"
        notes={[
          "Phase 1 uses a local placeholder provider instead of a third-party chart runtime.",
          "Future providers can attach richer chart engines without changing this panel contract."
        ]}
      />

      {isLoading ? (
        <div className="stateBlock">
          <strong>Loading trade diagnostics...</strong>
          <p>The selected trade details are being fetched from the API.</p>
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="stateBlock isError">
          <strong>Trade detail unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {!isLoading && !error ? (
        <>
          <div className="chartBlock payoffBlock">
            <span className="chartLabel">Payoff sketch</span>
            <svg
              viewBox="0 0 320 110"
              className="lineChart payoff"
              role="img"
              aria-label="Illustrative payoff curve"
            >
              <polyline points={buildPayoffPoints(activeTrade.payoff)} />
            </svg>
          </div>

          <div className="scenarioWrap">
            <div className="sectionSubheader">
              <p className="eyebrow">Scenario grid</p>
              <span className="sectionMeta">Underlying move x IV move</span>
            </div>
            <div className="scenarioTable">
              <div className="scenarioHeader">Move</div>
              <div className="scenarioHeader mono">IV -1</div>
              <div className="scenarioHeader mono">IV flat</div>
              <div className="scenarioHeader mono">IV +1</div>
              {activeTrade.scenario.map((row) => (
                <div
                  className="scenarioRow"
                  key={row.move}
                >
                  <div className="scenarioLabel">{row.move}</div>
                  {row.pnl.map((value, index) => (
                    <div
                      key={`${row.move}-${index}`}
                      className={value >= 0 ? "scenarioValue positive" : "scenarioValue negative"}
                    >
                      {value.toFixed(1)}R
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>

          <div className="greekGrid">
            <div>
              <span className="detailLabel">Delta</span>
              <strong className="mono">{activeTrade.greeks.delta.toFixed(2)}</strong>
            </div>
            <div>
              <span className="detailLabel">Gamma</span>
              <strong className="mono">{activeTrade.greeks.gamma.toFixed(2)}</strong>
            </div>
            <div>
              <span className="detailLabel">Vega</span>
              <strong className="mono">{activeTrade.greeks.vega.toFixed(2)}</strong>
            </div>
            <div>
              <span className="detailLabel">Theta</span>
              <strong className="mono">{activeTrade.greeks.theta.toFixed(2)}</strong>
            </div>
          </div>

          <div className="sectionSubheader">
            <p className="eyebrow">Execution notes</p>
          </div>
          <ul className="plainList">
            {activeTrade.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
