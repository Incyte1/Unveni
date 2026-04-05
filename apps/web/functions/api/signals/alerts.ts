import { buildSignalAlertsFallback } from "../../_data";
import { proxyOrFallback, type PagesFunctionContext } from "../../_utils";

export const onRequestGet = async (context: PagesFunctionContext) => {
  const search = new URL(context.request.url).search;
  return proxyOrFallback(context, `/signals/alerts${search}`, buildSignalAlertsFallback());
};
