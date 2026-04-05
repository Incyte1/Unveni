import { proxyRequest, type PagesFunctionContext } from "../../_utils";

export const onRequestPost = async (context: PagesFunctionContext) =>
  proxyRequest(context, "/watchlist/items", {
    method: "POST",
    body: await context.request.text(),
    headers: {
      "content-type": context.request.headers.get("content-type") ?? "application/json"
    }
  });
