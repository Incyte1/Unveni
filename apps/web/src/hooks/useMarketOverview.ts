import { getMarketOverview, toErrorMessage } from "../lib/api";
import type { MarketOverviewResponse } from "../lib/contracts";
import { useResource } from "./useResource";

export function useMarketOverview() {
  return useResource<MarketOverviewResponse>(
    async (signal) => {
      try {
        return await getMarketOverview(signal);
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    []
  );
}
