import { buildSignalsFallback } from "../_data";
import { proxyOrFallback, type PagesFunctionContext } from "../_utils";

export const onRequestGet = async (context: PagesFunctionContext) =>
  proxyOrFallback(context, "/signals", buildSignalsFallback());
