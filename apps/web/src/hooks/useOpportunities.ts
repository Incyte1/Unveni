import { getOpportunities, toErrorMessage } from "../lib/api";
import type { OpportunitiesResponse } from "../lib/contracts";
import { useResource } from "./useResource";

export function useOpportunities() {
  return useResource<OpportunitiesResponse>(
    async (signal) => {
      try {
        return await getOpportunities(signal);
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    []
  );
}
