import type { Opportunity } from "../data/mock";

interface TradeDetailDrawerProps {
  item: Opportunity;
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

export function TradeDetailDrawer({ item }: TradeDetailDrawerProps) {
  return (
    <section className="panel reveal inspector">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Selected trade</p>
          <h2>
            {item.symbol} {item.structure}
          </h2>
        </div>
        <span className="scorePill mono">{item.score}</span>
      </div>

      <p className="detailCopy">{item.thesis}</p>

      <div className="detailGrid">
        <div>
          <span className="detailLabel">DTE</span>
          <strong className="mono">{item.dte}</strong>
        </div>
        <div>
          <span className="detailLabel">Max loss</span>
          <strong className="mono">${item.maxLoss.toFixed(2)}</strong>
        </div>
        <div>
          <span className="detailLabel">IV rank</span>
          <strong className="mono">{item.ivRank}</strong>
        </div>
        <div>
          <span className="detailLabel">Spread</span>
          <strong className="mono">{item.spreadBps} bps</strong>
        </div>
      </div>

      <div className="chartBlock payoffBlock">
        <span className="chartLabel">Payoff sketch</span>
        <svg
          viewBox="0 0 320 110"
          className="lineChart payoff"
          role="img"
          aria-label="Illustrative payoff curve"
        >
          <polyline points={buildPayoffPoints(item.payoff)} />
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
          {item.scenario.map((row) => (
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
          <strong className="mono">{item.delta.toFixed(2)}</strong>
        </div>
        <div>
          <span className="detailLabel">Gamma</span>
          <strong className="mono">{item.gamma.toFixed(2)}</strong>
        </div>
        <div>
          <span className="detailLabel">Vega</span>
          <strong className="mono">{item.vega.toFixed(2)}</strong>
        </div>
        <div>
          <span className="detailLabel">Theta</span>
          <strong className="mono">{item.theta.toFixed(2)}</strong>
        </div>
      </div>

      <div className="sectionSubheader">
        <p className="eyebrow">Top drivers</p>
      </div>
      <ul className="plainList">
        {item.topDrivers.map((driver) => (
          <li key={driver}>{driver}</li>
        ))}
      </ul>

      <div className="sectionSubheader">
        <p className="eyebrow">Execution notes</p>
      </div>
      <ul className="plainList">
        {item.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}

