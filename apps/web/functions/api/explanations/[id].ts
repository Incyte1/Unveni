import { buildExplanationFallback } from "../../_data";
import {
  jsonResponse,
  proxyOrFallback,
  type PagesFunctionContext
} from "../../_utils";

export const onRequestGet = async (context: PagesFunctionContext) => {
  const tradeId = context.params?.id;

  if (!tradeId) {
    return jsonResponse({ error: "trade_id_required" }, 400);
  }

  const fallback = buildExplanationFallback(tradeId);
  if (!fallback && !context.env?.API_ORIGIN) {
    return jsonResponse({ error: "trade_not_found" }, 404);
  }

  return proxyOrFallback(context, `/explanations/${tradeId}`, fallback);
};
