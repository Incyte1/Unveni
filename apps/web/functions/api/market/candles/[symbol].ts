import { jsonResponse, proxyRequest, type PagesFunctionContext } from "../../../_utils";

export const onRequestGet = async (context: PagesFunctionContext) => {
  const symbol = context.params?.symbol;
  if (!symbol) {
    return jsonResponse({ error: { code: "symbol_required", message: "Symbol is required." } }, 400);
  }

  const url = new URL(context.request.url);
  const limit = url.searchParams.get("limit");
  const interval = url.searchParams.get("interval");
  const params = new URLSearchParams();
  if (interval) {
    params.set("interval", interval);
  }
  if (limit) {
    params.set("limit", limit);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return proxyRequest(context, `/market/candles/${encodeURIComponent(symbol)}${suffix}`);
};
