import type { BacktestSeries } from "../data/mock";

interface BacktestPanelProps {
  series: BacktestSeries;
}

function toPolyline(
  values: number[],
  height: number,
  width: number,
  min: number,
  max: number
) {
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / (max - min || 1)) * height;
      return `${x},${y}`;
    })
    .join(" ");
}

export function BacktestPanel({ series }: BacktestPanelProps) {
  const equityPoints = toPolyline(series.equity, 110, 380, 0.98, 1.2);
  const drawdownPoints = toPolyline(series.drawdown, 90, 380, 0, 0.04);

  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Research governance</p>
          <h2>Backtest pulse</h2>
        </div>
        <p className="sectionMeta">
          Walk-forward equity, drawdown, and calibration placeholders for the ranking stack.
        </p>
      </div>

      <div className="chartGrid">
        <div className="chartBlock">
          <span className="chartLabel">Equity curve</span>
          <svg
            viewBox="0 0 380 110"
            className="lineChart"
            role="img"
            aria-label="Illustrative equity curve"
          >
            <polyline points={equityPoints} />
          </svg>
        </div>
        <div className="chartBlock">
          <span className="chartLabel">Drawdown</span>
          <svg
            viewBox="0 0 380 90"
            className="lineChart drawdown"
            role="img"
            aria-label="Illustrative drawdown chart"
          >
            <polyline points={drawdownPoints} />
          </svg>
        </div>
      </div>

      <div className="metricCards">
        {series.metrics.map((metric) => (
          <div
            key={metric.label}
            className="metricCard"
          >
            <span>{metric.label}</span>
            <strong className="mono">{metric.value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

