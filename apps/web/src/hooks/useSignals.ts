import { getSignals, toErrorMessage } from "../lib/api";
import type { SignalsResponse } from "../lib/contracts";
import { useResource } from "./useResource";

export function useSignals(scopeKey: string) {
  return useResource<SignalsResponse>(
    async (signal) => {
      try {
        return await getSignals(signal);
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    [scopeKey],
    { refreshIntervalMs: 60_000 }
  );
}
