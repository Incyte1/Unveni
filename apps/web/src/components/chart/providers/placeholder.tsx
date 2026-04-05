import type { ChartProviderDefinition, ChartProviderProps } from "../types";

function buildSeries(symbol: string) {
  const seed = symbol
    .split("")
    .reduce((total, character) => total + character.charCodeAt(0), 0);

  return Array.from({ length: 12 }, (_, index) => {
    const wave = Math.sin((seed + index * 7) / 10) * 8;
    const drift = index * 2.4;
    return 42 + drift + wave;
  });
}

function toPolyline(values: number[]) {
  const width = 340;
  const height = 150;
  const min = Math.min(...values);
  const max = Math.max(...values);

  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / (max - min || 1)) * height;
      return `${x},${y}`;
    })
    .join(" ");
}

function PlaceholderChart({ model }: ChartProviderProps) {
  const points = toPolyline(buildSeries(model.symbol));

  return (
    <div className="chartProviderPlaceholder">
      <div className="chartProviderHeader">
        <div>
          <strong>{model.symbol}</strong>
          <p className="chartProviderCopy">
            Local placeholder provider. The chart contract is ready for future providers without
            changing the dashboard surface.
          </p>
        </div>
        <span className="tag mono">{model.timeframe}</span>
      </div>

      <svg
        viewBox="0 0 340 150"
        className="lineChart chartProviderLine"
        role="img"
        aria-label={`${model.symbol} placeholder price context`}
      >
        <polyline points={points} />
      </svg>

      <div className="chartCapabilityList">
        <span className="tag">Provider abstraction</span>
        <span className="tag">Future streaming feed</span>
        <span className="tag">Future TradingView slot</span>
      </div>

      {model.notes?.length ? (
        <ul className="plainList chartNoteList">
          {model.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export const placeholderChartProvider: ChartProviderDefinition = {
  id: "placeholder",
  label: "Placeholder chart provider",
  capabilities: {
    indicators: false,
    drawings: false,
    streaming: false
  },
  Component: PlaceholderChart
};
