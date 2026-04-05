import { buildSessionFallback } from "../_data";
import { proxyOrFallback, proxyRequest, type PagesFunctionContext } from "../_utils";

export const onRequestGet = async (context: PagesFunctionContext) =>
  proxyOrFallback(context, "/session", buildSessionFallback());

export const onRequestPost = async (context: PagesFunctionContext) =>
  proxyRequest(context, "/session", {
    method: "POST",
    body: await context.request.text(),
    headers: {
      "content-type": context.request.headers.get("content-type") ?? "application/json"
    }
  });
