import { useState, type FormEvent } from "react";
import type { WatchlistResponse } from "../lib/contracts";

interface WatchlistPanelProps {
  actionError: string | null;
  data: WatchlistResponse | null;
  error: string | null;
  isLoading: boolean;
  isSaving: boolean;
  onAdd: (symbol: string, notes: string) => Promise<boolean>;
  onRemove: (symbol: string) => Promise<boolean>;
  suggestedSymbol?: string;
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD"
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

export function WatchlistPanel({
  actionError,
  data,
  error,
  isLoading,
  isSaving,
  onAdd,
  onRemove,
  suggestedSymbol
}: WatchlistPanelProps) {
  const [symbol, setSymbol] = useState("");
  const [notes, setNotes] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const saved = await onAdd(symbol, notes);
    if (saved) {
      setSymbol("");
      setNotes("");
    }
  }

  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Persistence-backed</p>
          <h2>Watchlist</h2>
        </div>
        <p className="sectionMeta">Session-scoped symbols with notes and latest quote context.</p>
      </div>

      <form
        className="panelForm"
        onSubmit={handleSubmit}
      >
        <div className="formGrid compactFormGrid">
          <label>
            <span className="detailLabel">Symbol</span>
            <input
              className="searchInput"
              value={symbol}
              onChange={(event) => setSymbol(event.target.value)}
              placeholder="NVDA"
              maxLength={16}
            />
          </label>
          <label className="formFieldWide">
            <span className="detailLabel">Notes</span>
            <input
              className="searchInput"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Why it stays on radar"
              maxLength={280}
            />
          </label>
        </div>
        <div className="actionRow">
          <button
            className="primaryButton"
            type="submit"
            disabled={isSaving}
          >
            {isSaving ? "Saving..." : "Add symbol"}
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
          <strong>Watchlist update failed.</strong>
          <p>{actionError}</p>
        </div>
      ) : null}

      {isLoading ? (
        <div className="stateBlock">
          <strong>Loading watchlist...</strong>
          <p>The dashboard is waiting for persisted symbols for this session.</p>
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="stateBlock isError">
          <strong>Watchlist unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {!isLoading && !error && data && data.items.length === 0 ? (
        <div className="stateBlock">
          <strong>No watchlist symbols yet.</strong>
          <p>Add a symbol to persist it for the current signed-in session.</p>
        </div>
      ) : null}

      {!isLoading && !error && data && data.items.length > 0 ? (
        <div className="stackList">
          {data.items.map((item) => (
            <article
              key={item.symbol}
              className="watchlistCard"
            >
              <div className="watchlistCardTop">
                <div>
                  <strong>{item.symbol}</strong>
                  <p className="sectionMeta">
                    {currencyFormatter.format(item.quote.last)} -{" "}
                    <span className={item.quote.change >= 0 ? "positive mono" : "negative mono"}>
                      {item.quote.change >= 0 ? "+" : ""}
                      {currencyFormatter.format(item.quote.change)} ({item.quote.change >= 0 ? "+" : ""}
                      {percentFormatter.format(item.quote.change_percent)}%)
                    </span>
                  </p>
                </div>
                <button
                  className="dangerButton"
                  type="button"
                  onClick={() => void onRemove(item.symbol)}
                  disabled={isSaving}
                >
                  Remove
                </button>
              </div>
              <p className="detailCopy watchlistNotes">
                {item.notes ?? "No note attached yet."}
              </p>
              <div className="tagRow">
                <span className="tag mono">
                  {new Date(item.quote.as_of).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit"
                  })}
                </span>
                <span className="tag">{item.quote.source}</span>
                <span className="tag">{item.quote.quality}</span>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
