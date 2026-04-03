export function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8"
    }
  });
}

function objectBody(value: unknown) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  return {
    data: value
  };
}

export async function proxyOrFallback(
  context: any,
  path: string,
  fallback: unknown
) {
  const origin = context.env?.API_ORIGIN;

  if (!origin) {
    return jsonResponse({
      source: "edge-fallback",
      ...objectBody(fallback)
    });
  }

  try {
    const upstreamUrl = new URL(path, origin).toString();
    const upstream = await fetch(upstreamUrl, {
      headers: {
        "x-data-entitlement": context.data?.entitlement ?? "delayed-demo",
        "x-execution-mode": context.data?.executionMode ?? "paper"
      }
    });

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: {
        "content-type":
          upstream.headers.get("content-type") ?? "application/json; charset=utf-8"
      }
    });
  } catch {
    return jsonResponse({
      source: "edge-fallback",
      fallbackReason: "upstream_unavailable",
      ...objectBody(fallback)
    });
  }
}
