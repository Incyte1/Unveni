import { risk } from "../_data";
import { proxyOrFallback } from "../_utils";

export const onRequestGet = async (context: any) =>
  proxyOrFallback(context, "/risk", risk);

