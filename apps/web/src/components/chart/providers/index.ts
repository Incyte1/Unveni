import type { ChartProviderDefinition } from "../types";
import { placeholderChartProvider } from "./placeholder";

const providers: Record<string, ChartProviderDefinition> = {
  [placeholderChartProvider.id]: placeholderChartProvider
};

export function getChartProvider(providerId?: string) {
  if (providerId && providerId in providers) {
    return providers[providerId];
  }

  return placeholderChartProvider;
}
