import type {
  CandleHistoryResponse,
  CandleRecord,
  IntradayScorecardResponse,
  MarketClock,
  MarketOverviewResponse,
  QuoteSnapshot,
  SignalAlert,
  SignalAlertsResponse,
  SignalAlertStatusUpdateRequest,
  SignalHistoryResponse,
  SignalsResponse,
  SessionCreateRequest,
  PaperOrderPlacementResponse,
  PaperOrderRequest,
  PaperOrdersResponse,
  PaperPortfolioSummary,
  PaperPositionsResponse,
  OpportunitiesResponse,
  RiskSnapshot,
  SessionResponse,
  SymbolSearchResponse,
  TradeDetailResponse,
  TradeExplanationResponse,
  WatchlistDeleteResponse,
  WatchlistItemRecord,
  WatchlistItemUpsertRequest,
  WatchlistResponse
} from "./contracts";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(status: number, payload: unknown) {
    super(`API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function readErrorDetail(payload: unknown) {
  if (payload && typeof payload === "object") {
    const errorObject = "error" in payload ? payload.error : undefined;
    if (errorObject && typeof errorObject === "object") {
      const message = "message" in errorObject ? errorObject.message : undefined;
      if (typeof message === "string") {
        return message;
      }

      const code = "code" in errorObject ? errorObject.code : undefined;
      if (typeof code === "string") {
        return code;
      }
    }

    const detail = "detail" in payload ? payload.detail : undefined;
    if (typeof detail === "string") {
      return detail;
    }

    const error = "error" in payload ? payload.error : undefined;
    if (typeof error === "string") {
      return error;
    }
  }

  return null;
}

export function toErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    const detail = readErrorDetail(error.payload);
    return detail ?? error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected request failure.";
}

async function requestJson<T>(
  path: string,
  options: {
    body?: unknown;
    method?: string;
    signal?: AbortSignal;
  } = {}
): Promise<T> {
  const headers: Record<string, string> = {
    accept: "application/json"
  };
  const init: RequestInit = {
    method: options.method ?? "GET",
    credentials: "same-origin",
    headers,
    signal: options.signal
  };

  if (options.body !== undefined) {
    headers["content-type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }

  const response = await fetch(`/api${path}`, {
    ...init
  });
  const text = await response.text();
  const payload = text ? (JSON.parse(text) as T) : null;

  if (!response.ok) {
    throw new ApiError(response.status, payload);
  }

  return payload as T;
}

export function getSession(signal?: AbortSignal) {
  return requestJson<SessionResponse>("/session", { signal });
}

export function createSession(
  payload: SessionCreateRequest,
  signal?: AbortSignal
) {
  return requestJson<SessionResponse>("/session", {
    method: "POST",
    body: payload,
    signal
  });
}

export function logoutSession(signal?: AbortSignal) {
  return requestJson<SessionResponse>("/session/logout", {
    method: "POST",
    signal
  });
}

export function getOpportunities(signal?: AbortSignal) {
  return requestJson<OpportunitiesResponse>("/opportunities", { signal });
}

export function getTradeDetail(tradeId: string, signal?: AbortSignal) {
  return requestJson<TradeDetailResponse>(`/trade/${tradeId}`, { signal });
}

export function getRisk(signal?: AbortSignal) {
  return requestJson<RiskSnapshot>("/risk", { signal });
}

export function getMarketOverview(signal?: AbortSignal) {
  return requestJson<MarketOverviewResponse>("/market-overview", { signal });
}

export function getMarketClock(signal?: AbortSignal) {
  return requestJson<MarketClock>("/market/clock", { signal });
}

export function searchMarketSymbols(query: string, signal?: AbortSignal) {
  return requestJson<SymbolSearchResponse>(`/market/search?q=${encodeURIComponent(query)}`, {
    signal
  });
}

export function getMarketQuote(symbol: string, signal?: AbortSignal) {
  return requestJson<QuoteSnapshot>(`/market/quotes/${encodeURIComponent(symbol)}`, { signal });
}

export function getMarketCandles(symbol: string, limit = 60, signal?: AbortSignal) {
  return requestJson<CandleHistoryResponse>(
    `/market/candles/${encodeURIComponent(symbol)}?limit=${limit}`,
    { signal }
  );
}

export function getIntradayMarketCandles(
  symbol: string,
  interval: Extract<CandleRecord["interval"], "1min" | "5min" | "15min">,
  limit = 60,
  signal?: AbortSignal
) {
  return requestJson<CandleHistoryResponse>(
    `/market/candles/${encodeURIComponent(symbol)}?interval=${interval}&limit=${limit}`,
    { signal }
  );
}

export function getSignals(signal?: AbortSignal) {
  return requestJson<SignalsResponse>("/signals", { signal });
}

export function getSignalAlerts(
  options: {
    limit?: number;
    minutes?: number;
    status?: "new" | "read" | "acknowledged";
    signal?: AbortSignal;
  } = {}
) {
  const params = new URLSearchParams();
  if (options.limit) {
    params.set("limit", String(options.limit));
  }
  if (options.minutes) {
    params.set("minutes", String(options.minutes));
  }
  if (options.status) {
    params.set("status", options.status);
  }
  const query = params.toString();
  return requestJson<SignalAlertsResponse>(
    `/signals/alerts${query ? `?${query}` : ""}`,
    { signal: options.signal }
  );
}

export function getSignalAlertHistory(
  options: {
    limit?: number;
    status?: "new" | "read" | "acknowledged";
    signal?: AbortSignal;
  } = {}
) {
  const params = new URLSearchParams();
  if (options.limit) {
    params.set("limit", String(options.limit));
  }
  if (options.status) {
    params.set("status", options.status);
  }
  const query = params.toString();
  return requestJson<SignalAlertsResponse>(
    `/signals/alerts/history${query ? `?${query}` : ""}`,
    { signal: options.signal }
  );
}

export function updateSignalAlertStatus(
  alertId: string,
  payload: SignalAlertStatusUpdateRequest,
  signal?: AbortSignal
) {
  return requestJson<SignalAlert>(`/signals/alerts/${encodeURIComponent(alertId)}`, {
    method: "PATCH",
    body: payload,
    signal
  });
}

export function getSignalHistory(symbol: string, limit = 20, signal?: AbortSignal) {
  return requestJson<SignalHistoryResponse>(
    `/signals/history/${encodeURIComponent(symbol)}?limit=${limit}`,
    { signal }
  );
}

export function getIntradayScorecard(
  lookbackDays = 1,
  signal?: AbortSignal
) {
  return requestJson<IntradayScorecardResponse>(
    `/signals/scorecard?lookback_days=${lookbackDays}`,
    { signal }
  );
}

export function getTradeExplanation(tradeId: string, signal?: AbortSignal) {
  return requestJson<TradeExplanationResponse>(`/explanations/${tradeId}`, { signal });
}

export function getWatchlist(signal?: AbortSignal) {
  return requestJson<WatchlistResponse>("/watchlist", { signal });
}

export function addWatchlistItem(
  payload: WatchlistItemUpsertRequest,
  signal?: AbortSignal
) {
  return requestJson<WatchlistItemRecord>("/watchlist/items", {
    method: "POST",
    body: payload,
    signal
  });
}

export function removeWatchlistItem(symbol: string, signal?: AbortSignal) {
  return requestJson<WatchlistDeleteResponse>(
    `/watchlist/items/${encodeURIComponent(symbol)}`,
    {
      method: "DELETE",
      signal
    }
  );
}

export function getPaperPositions(signal?: AbortSignal) {
  return requestJson<PaperPositionsResponse>("/paper/positions", { signal });
}

export function getPaperOrders(signal?: AbortSignal) {
  return requestJson<PaperOrdersResponse>("/paper/orders", { signal });
}

export function getPaperSummary(signal?: AbortSignal) {
  return requestJson<PaperPortfolioSummary>("/paper/summary", { signal });
}

export function placePaperOrder(payload: PaperOrderRequest, signal?: AbortSignal) {
  return requestJson<PaperOrderPlacementResponse>("/paper/orders", {
    method: "POST",
    body: payload,
    signal
  });
}
