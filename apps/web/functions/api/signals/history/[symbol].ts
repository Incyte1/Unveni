import { buildSignalHistoryFallback } from "../../../_data";
import { proxyOrFallback, type PagesFunctionContext } from "../../../_utils";

export const onRequestGet = async (context: PagesFunctionContext) => {
  const search = new URL(context.request.url).search;
  const symbol = context.params?.symbol ?? "";
  return proxyOrFallback(
    context,
    `/signals/history/${encodeURIComponent(symbol)}${search}`,
    buildSignalHistoryFallback(symbol)
  );
};
