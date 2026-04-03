import { opportunities } from "../_data";
import { proxyOrFallback } from "../_utils";

export const onRequestGet = async (context: any) =>
  proxyOrFallback(context, "/opportunities", {
    asOf: new Date().toISOString(),
    items: opportunities
  });

