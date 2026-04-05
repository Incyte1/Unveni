import { jsonResponse, proxyRequest, type PagesFunctionContext } from "../../../_utils";

export const onRequestDelete = async (context: PagesFunctionContext) => {
  const symbol = context.params?.symbol;

  if (!symbol) {
    return jsonResponse({ error: "symbol_required" }, 400);
  }

  return proxyRequest(context, `/watchlist/items/${encodeURIComponent(symbol)}`, {
    method: "DELETE"
  });
};
