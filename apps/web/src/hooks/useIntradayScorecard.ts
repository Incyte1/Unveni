import { getIntradayScorecard, toErrorMessage } from "../lib/api";
import type { IntradayScorecardResponse } from "../lib/contracts";
import { useResource } from "./useResource";

export function useIntradayScorecard(
  scopeKey: string,
  enabled: boolean,
  lookbackDays = 1
) {
  return useResource<IntradayScorecardResponse>(
    async (signal) => {
      try {
        return await getIntradayScorecard(lookbackDays, signal);
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    [scopeKey, lookbackDays],
    {
      enabled,
      refreshIntervalMs: 60_000
    }
  );
}
