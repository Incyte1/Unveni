import { getChartProvider } from "./providers";
import type { ChartModel } from "./types";

interface ChartContainerProps {
  symbol: string;
  providerId?: string;
  timeframe?: string;
  title?: string;
  notes?: string[];
}

export function ChartContainer({
  symbol,
  providerId,
  timeframe = "1D",
  title,
  notes
}: ChartContainerProps) {
  const provider = getChartProvider(providerId);
  const Provider = provider.Component;
  const model: ChartModel = {
    symbol,
    timeframe,
    headline: title,
    notes
  };

  return (
    <section className="chartPanel">
      <div className="sectionSubheader">
        <p className="eyebrow">{title ?? "Underlying chart"}</p>
        <span className="sectionMeta">{provider.label}</span>
      </div>
      <div className="chartSurface">
        <Provider model={model} />
      </div>
    </section>
  );
}
