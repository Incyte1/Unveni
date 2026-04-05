import { useState, type FormEvent } from "react";
import type { PaperTradingDashboard } from "../hooks/usePaperTrading";

interface PaperTradingPanelProps {
  actionError: string | null;
  data: PaperTradingDashboard | null;
  error: string | null;
  isLoading: boolean;
  isSubmitting: boolean;
  onSubmit: (input: {
    quantity: number;
    side: "buy" | "sell";
    symbol: string;
  }) => Promise<unknown>;
  suggestedSymbol?: string;
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD"
});

export function PaperTradingPanel({
  actionError,
  data,
  error,
  isLoading,
  isSubmitting,
  onSubmit,
  suggestedSymbol
}: PaperTradingPanelProps) {
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [side, setSide] = useState<"buy" | "sell">("buy");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedQuantity = Number(quantity);
    const response = await onSubmit({
      symbol,
      side,
      quantity: Number.isFinite(parsedQuantity) ? parsedQuantity : 0
    });

    if (response) {
      setQuantity("1");
    }
  }

  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Phase 2</p>
          <h2>Paper trading</h2>
        </div>
        <p className="sectionMeta">Deterministic market-order execution with persisted positions and order history.</p>
      </div>

      <form
        className="panelForm"
        onSubmit={handleSubmit}
      >
        <div className="formGrid">
          <label>
            <span className="detailLabel">Symbol</span>
            <input
              className="searchInput"
              value={symbol}
              onChange={(event) => setSymbol(event.target.value)}
              placeholder="AAPL"
              maxLength={16}
            />
          </label>
          <label>
            <span className="detailLabel">Side</span>
            <select
              className="searchInput"
              value={side}
              onChange={(event) => setSide(event.target.value as "buy" | "sell")}
            >
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>
          <label>
            <span className="detailLabel">Quantity</span>
            <input
              className="searchInput"
              type="number"
              min="1"
              step="1"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
            />
          </label>
        </div>
        <div className="actionRow">
          <button
            className="primaryButton"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Submitting..." : "Place paper order"}
          </button>
          {suggestedSymbol ? (
            <button
              className="secondaryButton"
              type="button"
              onClick={() => setSymbol(suggestedSymbol)}
            >
              Use selected {suggestedSymbol}
            </button>
          ) : null}
        </div>
      </form>

      {actionError ? (
        <div className="stateBlock isError">
          <strong>Paper order failed.</strong>
          <p>{actionError}</p>
        </div>
      ) : null}

      {isLoading ? (
        <div className="stateBlock">
          <strong>Loading paper portfolio...</strong>
          <p>The dashboard is fetching open positions, order history, and summary metrics.</p>
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="stateBlock isError">
          <strong>Paper trading unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {!isLoading && !error && data ? (
        <>
          <div className="metricCards">
            <div className="metricCard">
              <span>Open positions</span>
              <strong>{data.summary.positions}</strong>
            </div>
            <div className="metricCard">
              <span>Market value</span>
              <strong>{currencyFormatter.format(data.summary.market_value)}</strong>
            </div>
            <div className="metricCard">
              <span>Unrealized P&amp;L</span>
              <strong className={data.summary.unrealized_pnl >= 0 ? "positive" : "negative"}>
                {currencyFormatter.format(data.summary.unrealized_pnl)}
              </strong>
            </div>
            <div className="metricCard">
              <span>Realized P&amp;L</span>
              <strong className={data.summary.realized_pnl >= 0 ? "positive" : "negative"}>
                {currencyFormatter.format(data.summary.realized_pnl)}
              </strong>
            </div>
          </div>

          <div className="signalBoardMeta">
            <span>Pricing source {data.summary.market_data_source}</span>
            <span>Quality {data.summary.market_data_quality}</span>
          </div>

          <div className="sectionSubheader">
            <p className="eyebrow">Open positions</p>
          </div>
          {data.positions.items.length === 0 ? (
            <div className="stateBlock">
              <strong>No open paper positions.</strong>
              <p>Buy a symbol to create the first persisted position for this signed-in session.</p>
            </div>
          ) : (
            <div className="stackList">
              {data.positions.items.map((position) => (
                <article
                  key={position.symbol}
                  className="positionCard"
                >
                  <div className="watchlistCardTop">
                    <div>
                      <strong>{position.symbol}</strong>
                      <p className="sectionMeta">
                        {position.quantity} shares - avg {currencyFormatter.format(position.average_cost)}
                      </p>
                    </div>
                    <strong className={position.total_pnl >= 0 ? "positive mono" : "negative mono"}>
                      {currencyFormatter.format(position.total_pnl)}
                    </strong>
                  </div>
                  <div className="positionStats">
                    <span>Market {currencyFormatter.format(position.market_price)}</span>
                    <span>Value {currencyFormatter.format(position.market_value)}</span>
                    <span className={position.unrealized_pnl >= 0 ? "positive" : "negative"}>
                      Unrealized {currencyFormatter.format(position.unrealized_pnl)}
                    </span>
                    <span className={position.realized_pnl >= 0 ? "positive" : "negative"}>
                      Realized {currencyFormatter.format(position.realized_pnl)}
                    </span>
                    <span>{position.market_source}</span>
                    <span>{position.market_quality}</span>
                  </div>
                </article>
              ))}
            </div>
          )}

          <div className="sectionSubheader">
            <p className="eyebrow">Order history</p>
          </div>
          {data.orders.items.length === 0 ? (
            <div className="stateBlock">
              <strong>No paper orders yet.</strong>
              <p>Market orders are executed immediately and will appear here once submitted.</p>
            </div>
          ) : (
            <div className="stackList">
              {data.orders.items.map((order) => (
                <article
                  key={order.id}
                  className="orderCard"
                >
                  <div className="watchlistCardTop">
                    <div>
                      <strong>
                        {order.side.toUpperCase()} {order.quantity} {order.symbol}
                      </strong>
                      <p className="sectionMeta">
                        Requested {currencyFormatter.format(order.requested_price)}
                        {order.fill_price ? ` - Filled ${currencyFormatter.format(order.fill_price)}` : ""}
                      </p>
                    </div>
                    <span className={`warningTag is${order.status === "filled" ? "low" : "risk"}`}>
                      {order.status}
                    </span>
                  </div>
                  <p className="detailCopy watchlistNotes">
                    {order.rejection_reason
                      ? order.rejection_reason
                      : `Submitted ${new Date(order.submitted_at).toLocaleString("en-US")}`}
                  </p>
                </article>
              ))}
            </div>
          )}

          <div className="callout">
            Fill model: {data.summary.assumptions.fill_model} Price source: {data.summary.assumptions.price_source}
          </div>
        </>
      ) : null}
    </section>
  );
}
