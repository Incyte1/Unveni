import { proxyRequest, type PagesFunctionContext } from "../../_utils";

export const onRequestGet = async (context: PagesFunctionContext) =>
  proxyRequest(context, "/paper/positions");
