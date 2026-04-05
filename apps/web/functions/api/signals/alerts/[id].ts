import { proxyRequest, type PagesFunctionContext } from "../../../_utils";

export const onRequestPatch = async (context: PagesFunctionContext) =>
  proxyRequest(context, `/signals/alerts/${encodeURIComponent(context.params?.id ?? "")}`, {
    method: "PATCH",
    headers: {
      "content-type": "application/json"
    },
    body: await context.request.text()
  });
