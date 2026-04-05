import { buildMarketOverviewFallback } from "../_data";
import { proxyOrFallback, type PagesFunctionContext } from "../_utils";

export const onRequestGet = async (context: PagesFunctionContext) =>
  proxyOrFallback(context, "/market-overview", buildMarketOverviewFallback());
