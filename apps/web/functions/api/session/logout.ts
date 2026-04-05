import { proxyRequest, type PagesFunctionContext } from "../../_utils";

export const onRequestPost = async (context: PagesFunctionContext) =>
  proxyRequest(context, "/session/logout", {
    method: "POST"
  });
