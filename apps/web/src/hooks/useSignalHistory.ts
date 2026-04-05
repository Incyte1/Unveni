import { getSignalHistory, toErrorMessage } from "../lib/api";
import type { SignalHistoryResponse } from "../lib/contracts";
import { useResource } from "./useResource";

export function useSignalHistory(
  symbol: string,
  scopeKey: string,
  enabled: boolean
) {
  return useResource<SignalHistoryResponse>(
    async (signal) => {
      try {
        return await getSignalHistory(symbol, 12, signal);
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    [scopeKey, symbol],
    {
      enabled: enabled && Boolean(symbol),
      refreshIntervalMs: 60_000
    }
  );
}
