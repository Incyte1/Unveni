export async function onRequest(context: any) {
  context.data = context.data ?? {};
  const entitlement =
    context.request.headers.get("x-data-entitlement") ?? "delayed-demo";
  const executionMode =
    context.request.headers.get("x-execution-mode") ?? "paper";

  context.data.entitlement = entitlement;
  context.data.executionMode = executionMode;

  const response = await context.next();

  if (new URL(context.request.url).pathname.startsWith("/api/")) {
    response.headers.set("Cache-Control", "public, max-age=15, s-maxage=60");
    response.headers.set("X-Data-Entitlement", entitlement);
    response.headers.set("X-Execution-Mode", executionMode);
    response.headers.set("X-Content-Type-Options", "nosniff");
    response.headers.set("X-Frame-Options", "DENY");
  }

  return response;
}
