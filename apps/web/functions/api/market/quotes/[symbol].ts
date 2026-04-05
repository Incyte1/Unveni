import { jsonResponse, proxyRequest, type PagesFunctionContext } from "../../../_utils";

export const onRequestGet = async (context: PagesFunctionContext) => {
  const symbol = context.params?.symbol;
  if (!symbol) {
    return jsonResponse({ error: { code: "symbol_required", message: "Symbol is required." } }, 400);
  }

  return proxyRequest(context, `/market/quotes/${encodeURIComponent(symbol)}`);
};
