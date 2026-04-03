import { tradeDetails } from "../../_data";
import { jsonResponse, proxyOrFallback } from "../../_utils";

export const onRequestGet = async (context: any) => {
  const tradeId = context.params?.id;

  if (!tradeId) {
    return jsonResponse({ error: "trade_id_required" }, 400);
  }

  if (!(tradeId in tradeDetails) && !context.env?.API_ORIGIN) {
    return jsonResponse({ error: "trade_not_found" }, 404);
  }

  return proxyOrFallback(
    context,
    `/opportunities/${tradeId}`,
    tradeDetails[tradeId as keyof typeof tradeDetails]
  );
};
