import { proxyRequest, type PagesFunctionContext } from "../../_utils";

export const onRequestGet = async (context: PagesFunctionContext) =>
  proxyRequest(context, "/paper/orders");

export const onRequestPost = async (context: PagesFunctionContext) =>
  proxyRequest(context, "/paper/orders", {
    method: "POST",
    body: await context.request.text(),
    headers: {
      "content-type": context.request.headers.get("content-type") ?? "application/json"
    }
  });
