interface Env {
  API_ORIGIN?: string;
  APP_NAME?: string;
}

export interface PagesFunctionContext {
  data?: Record<string, unknown>;
  env?: Env;
  next: () => Promise<Response>;
  params?: Record<string, string | undefined>;
  request: Request;
}

export function jsonResponse(
  body: unknown,
  status = 200,
  headers: HeadersInit = {}
) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...headers
    }
  });
}

async function proxyResponse(
  context: PagesFunctionContext,
  path: string,
  init: RequestInit = {}
) {
  const origin = context.env?.API_ORIGIN;
  if (!origin) {
    return null;
  }

  const headers = new Headers(init.headers);
  headers.set("accept", "application/json");

  const incomingCookie = context.request.headers.get("cookie");
  if (incomingCookie && !headers.has("cookie")) {
    headers.set("cookie", incomingCookie);
  }

  const upstreamUrl = new URL(path, origin).toString();
  const upstream = await fetch(upstreamUrl, {
    method: init.method ?? context.request.method,
    headers,
    body: init.body,
    redirect: "manual"
  });

  const text = await upstream.text();
  const responseHeaders = new Headers();
  for (const headerName of [
    "cache-control",
    "content-type",
    "set-cookie",
    "x-unveni-entitlement",
    "x-unveni-execution-mode",
    "x-unveni-session-mode"
  ]) {
    const value = upstream.headers.get(headerName);
    if (value) {
      responseHeaders.set(headerName, value);
    }
  }

  return new Response(text, {
    status: upstream.status,
    headers: responseHeaders
  });
}

export async function proxyOrFallback<T>(
  context: PagesFunctionContext,
  path: string,
  fallback: T
) {
  try {
    const proxied = await proxyResponse(context, path);
    if (proxied) {
      return proxied;
    }
  } catch {
    return jsonResponse(fallback);
  }

  return jsonResponse(fallback);
}

export async function proxyRequest(
  context: PagesFunctionContext,
  path: string,
  init: RequestInit = {}
) {
  if (!context.env?.API_ORIGIN) {
    return jsonResponse({ error: { code: "api_origin_not_configured", message: "API origin is not configured." } }, 503);
  }

  try {
    const proxied = await proxyResponse(context, path, init);
    if (!proxied) {
      return jsonResponse({ error: { code: "api_origin_not_configured", message: "API origin is not configured." } }, 503);
    }
    return proxied;
  } catch {
    return jsonResponse({ error: { code: "upstream_unavailable", message: "Upstream API is unavailable." } }, 503);
  }
}
