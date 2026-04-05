import type { ComponentType } from "react";

export interface ChartModel {
  symbol: string;
  timeframe: string;
  headline?: string;
  notes?: string[];
}

export interface ChartProviderProps {
  model: ChartModel;
}

export interface ChartProviderDefinition {
  id: string;
  label: string;
  capabilities: {
    indicators: boolean;
    drawings: boolean;
    streaming: boolean;
  };
  Component: ComponentType<ChartProviderProps>;
}
