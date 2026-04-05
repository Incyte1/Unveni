import { jsonResponse, proxyRequest, type PagesFunctionContext } from "../../_utils";

export const onRequestGet = async (context: PagesFunctionContext) => {
  const url = new URL(context.request.url);
  const query = url.searchParams.get("q");
  const limit = url.searchParams.get("limit");

  if (!query) {
    return jsonResponse({ error: { code: "query_required", message: "Search query is required." } }, 400);
  }

  const suffix = limit ? `?q=${encodeURIComponent(query)}&limit=${encodeURIComponent(limit)}` : `?q=${encodeURIComponent(query)}`;
  return proxyRequest(context, `/market/search${suffix}`);
};
