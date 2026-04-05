import { getRisk, toErrorMessage } from "../lib/api";
import type { RiskSnapshot } from "../lib/contracts";
import { useResource } from "./useResource";

export function useRisk() {
  return useResource<RiskSnapshot>(
    async (signal) => {
      try {
        return await getRisk(signal);
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    []
  );
}
