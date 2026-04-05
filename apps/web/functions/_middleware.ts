import { type PagesFunctionContext } from "./_utils";

function cacheControlForPath(pathname: string) {
  if (
    pathname === "/api/session" ||
    pathname.startsWith("/api/explanations/") ||
    pathname.startsWith("/api/signals") ||
    pathname.startsWith("/api/watchlist") ||
    pathname.startsWith("/api/paper")
  ) {
    return "private, no-store";
  }

  return "public, max-age=15, s-maxage=60";
}

export async function onRequest(context: PagesFunctionContext) {
  const response = await context.next();
  const pathname = new URL(context.request.url).pathname;

  if (pathname.startsWith("/api/")) {
    response.headers.set("Cache-Control", cacheControlForPath(pathname));
    response.headers.set("X-Content-Type-Options", "nosniff");
    response.headers.set("X-Frame-Options", "DENY");
    response.headers.append("Vary", "Cookie");
  }

  return response;
}
