import { useEffect, useState } from "react";
import {
  getPaperOrders,
  getPaperPositions,
  getPaperSummary,
  placePaperOrder,
  toErrorMessage
} from "../lib/api";
import type {
  PaperOrderPlacementResponse,
  PaperOrderRequest,
  PaperOrdersResponse,
  PaperPortfolioSummary,
  PaperPositionsResponse
} from "../lib/contracts";
import { useResource } from "./useResource";

export interface PaperTradingDashboard {
  orders: PaperOrdersResponse;
  positions: PaperPositionsResponse;
  summary: PaperPortfolioSummary;
}

export function usePaperTrading(enabled: boolean, scopeKey: string) {
  const resource = useResource<PaperTradingDashboard>(
    async (signal) => {
      try {
        const [positions, orders, summary] = await Promise.all([
          getPaperPositions(signal),
          getPaperOrders(signal),
          getPaperSummary(signal)
        ]);

        return {
          orders,
          positions,
          summary
        };
      } catch (error) {
        throw new Error(toErrorMessage(error));
      }
    },
    [scopeKey],
    { enabled }
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastOrder, setLastOrder] = useState<PaperOrderPlacementResponse | null>(null);

  useEffect(() => {
    if (!enabled) {
      setActionError(null);
      setIsSubmitting(false);
      setLastOrder(null);
    }
  }, [enabled, scopeKey]);

  async function submitOrder(payload: PaperOrderRequest) {
    setIsSubmitting(true);
    setActionError(null);

    try {
      const response = await placePaperOrder(payload);
      setLastOrder(response);
      resource.reload();
      return response;
    } catch (error) {
      setActionError(toErrorMessage(error));
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }

  return {
    ...resource,
    actionError,
    isSubmitting,
    lastOrder,
    submitOrder
  };
}
