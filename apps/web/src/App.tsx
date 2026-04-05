import { startTransition, useDeferredValue, useEffect, useState } from "react";
import { ActionableSignalsPanel } from "./components/ActionableSignalsPanel";
import { Header } from "./components/Header";
import { IntradayScorecardPanel } from "./components/IntradayScorecardPanel";
import { MarketOverviewPanel } from "./components/MarketOverviewPanel";
import { OpportunitiesTable } from "./components/OpportunitiesTable";
import { PaperTradingPanel } from "./components/PaperTradingPanel";
import { RiskPanel } from "./components/RiskPanel";
import { SignalAlertsPanel } from "./components/SignalAlertsPanel";
import { SignalInspector } from "./components/SignalInspector";
import { SessionPanel } from "./components/SessionPanel";
import { WatchlistPanel } from "./components/WatchlistPanel";
import { WhatShouldIDoNowPanel } from "./components/WhatShouldIDoNowPanel";
import { useIntradayScorecard } from "./hooks/useIntradayScorecard";
import { useMarketOverview } from "./hooks/useMarketOverview";
import { useOpportunities } from "./hooks/useOpportunities";
import { usePaperTrading } from "./hooks/usePaperTrading";
import { useRisk } from "./hooks/useRisk";
import { useSignalAlerts } from "./hooks/useSignalAlerts";
import { useSignalHistory } from "./hooks/useSignalHistory";
import { useSession } from "./hooks/useSession";
import { useSignals } from "./hooks/useSignals";
import { useWatchlist } from "./hooks/useWatchlist";

type SetupFilter = "All" | string;

export default function App() {
  const [query, setQuery] = useState("");
  const [setupFilter, setSetupFilter] = useState<SetupFilter>("All");
  const [selectedId, setSelectedId] = useState("");
  const [selectedSignalSymbol, setSelectedSignalSymbol] = useState("");
  const [alertWindowMinutes, setAlertWindowMinutes] = useState(30);
  const deferredQuery = useDeferredValue(query);
  const session = useSession();
  const isAuthenticated = session.data?.is_authenticated ?? false;
  const sessionScopeKey = session.data?.user?.id ?? "anonymous";
  const signals = useSignals(sessionScopeKey);
  const signalAlerts = useSignalAlerts(sessionScopeKey, {
    enabled: isAuthenticated,
    limit: 12,
    minutes: alertWindowMinutes
  });
  const scorecard = useIntradayScorecard(sessionScopeKey, isAuthenticated, 1);
  const opportunities = useOpportunities();
  const risk = useRisk();
  const marketOverview = useMarketOverview();
  const watchlist = useWatchlist(isAuthenticated, sessionScopeKey);
  const paperTrading = usePaperTrading(isAuthenticated, sessionScopeKey);

  const setupFilters: SetupFilter[] = [
    "All",
    ...new Set(signals.data?.items.map((item) => item.strategy_type) ?? [])
  ];

  const filteredSignals = (signals.data?.items ?? []).filter((item) => {
    const queryText = deferredQuery.toLowerCase();
    if (!queryText) {
      return true;
    }

    return (
      item.symbol.toLowerCase().includes(queryText) ||
      item.strategy_type.toLowerCase().includes(queryText) ||
      item.thesis.toLowerCase().includes(queryText) ||
      item.reasons.some((reason) => reason.toLowerCase().includes(queryText))
    ) && (setupFilter === "All" || item.strategy_type === setupFilter);
  });

  const filteredOpportunities = (opportunities.data?.items ?? []).filter((item) => {
    const matchesQuery =
      item.symbol.toLowerCase().includes(deferredQuery.toLowerCase()) ||
      item.structure.toLowerCase().includes(deferredQuery.toLowerCase()) ||
      item.thesis.toLowerCase().includes(deferredQuery.toLowerCase());

    return matchesQuery;
  });

  useEffect(() => {
    if (!selectedSignalSymbol && filteredSignals.length > 0) {
      setSelectedSignalSymbol(filteredSignals[0].symbol);
      return;
    }

    if (
      selectedSignalSymbol &&
      !filteredSignals.some((item) => item.symbol === selectedSignalSymbol) &&
      filteredSignals.length > 0
    ) {
      setSelectedSignalSymbol(filteredSignals[0].symbol);
      return;
    }

    if (filteredSignals.length === 0) {
      setSelectedSignalSymbol("");
    }
  }, [filteredSignals, selectedSignalSymbol]);

  useEffect(() => {
    if (!selectedId && filteredOpportunities.length > 0) {
      setSelectedId(filteredOpportunities[0].id);
      return;
    }

    if (
      selectedId &&
      !filteredOpportunities.some((item) => item.id === selectedId) &&
      filteredOpportunities.length > 0
    ) {
      setSelectedId(filteredOpportunities[0].id);
      return;
    }

    if (filteredOpportunities.length === 0) {
      setSelectedId("");
    }
  }, [filteredOpportunities, selectedId]);

  const selectedSignal =
    filteredSignals.find((item) => item.symbol === selectedSignalSymbol) ?? filteredSignals[0] ?? null;
  const selectedOpportunity =
    filteredOpportunities.find((item) => item.id === selectedId) ?? filteredOpportunities[0];

  useEffect(() => {
    if (
      selectedSignal?.opportunity_id &&
      filteredOpportunities.some((item) => item.id === selectedSignal.opportunity_id) &&
      selectedSignal.opportunity_id !== selectedId
    ) {
      setSelectedId(selectedSignal.opportunity_id);
    }
  }, [filteredOpportunities, selectedId, selectedSignal?.opportunity_id]);

  function handleSelectSignal(symbol: string) {
    setSelectedSignalSymbol(symbol);
    const matchedSignal = signals.data?.items.find((item) => item.symbol === symbol);
    if (matchedSignal?.opportunity_id) {
      setSelectedId(matchedSignal.opportunity_id);
    }
  }

  function handleSelectOpportunity(id: string) {
    setSelectedId(id);
    const matchedOpportunity =
      filteredOpportunities.find((item) => item.id === id) ??
      opportunities.data?.items.find((item) => item.id === id);

    if (matchedOpportunity) {
      setSelectedSignalSymbol(matchedOpportunity.symbol);
    }
  }

  const actionableCount = filteredSignals.filter((item) => item.is_actionable).length;
  const suggestedSymbol = selectedSignal?.symbol ?? selectedOpportunity?.symbol;
  const signalHistory = useSignalHistory(
    selectedSignal?.symbol ?? "",
    sessionScopeKey,
    isAuthenticated && Boolean(selectedSignal?.symbol)
  );

  return (
    <div className="appShell">
      <Header
        actionableCount={actionableCount}
        signalCount={filteredSignals.length}
        session={session.data}
        sessionError={session.error}
        isSessionLoading={session.isLoading}
        isSessionSaving={session.isSaving}
        onLogout={session.endSession}
        refreshedAt={signals.data?.as_of ?? opportunities.data?.as_of ?? marketOverview.data?.as_of ?? null}
      />

      <main className="workspace">
        <aside className="panel navPanel reveal">
          <div className="sectionHeader">
            <div>
              <p className="eyebrow">Decision scope</p>
              <h2>Filters</h2>
            </div>
          </div>

          <label
            className="searchField"
            htmlFor="trade-search"
          >
            Search symbol or structure
          </label>
          <input
            id="trade-search"
            className="searchInput"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="NVDA, calendar, iron condor..."
          />

          <div className="sectionSubheader">
            <p className="eyebrow">Setups</p>
          </div>
          <div className="filterList">
            {setupFilters.map((option) => (
              <button
                key={option}
                type="button"
                className={option === setupFilter ? "filterChip isSelected" : "filterChip"}
                onClick={() => {
                  startTransition(() => {
                    setSetupFilter(option);
                  });
                }}
              >
                {option}
              </button>
            ))}
          </div>

          <div className="sectionSubheader">
            <p className="eyebrow">Engine rules</p>
          </div>
          <ul className="plainList">
            <li>Signals now come from intraday opening range, VWAP, pullback, rejection, and hard risk gates.</li>
            <li>Existing paper positions flip fresh entries into HOLD, REDUCE, or EXIT instead of duplicating the trade.</li>
            <li>NO_TRADE is deliberate: the engine stands aside when session timing, structure, or risk is not good enough.</li>
          </ul>

          <div className="callout">
            Data posture: the engine stays deterministic and intraday-first. No fake AI claims and no broker execution.
          </div>
        </aside>

        <section className="mainColumn">
          <WhatShouldIDoNowPanel
            alerts={signals.data?.alerts ?? []}
            error={signals.error}
            focus={signals.data?.focus ?? null}
            isLoading={signals.isLoading}
            marketClock={signals.data?.market_clock ?? null}
            marketDataQuality={signals.data?.market_data_quality ?? null}
            marketDataSource={signals.data?.market_data_source ?? null}
            portfolio={signals.data?.portfolio ?? null}
            onSelectSignal={handleSelectSignal}
          />
          <ActionableSignalsPanel
            data={signals.data}
            error={signals.error}
            isLoading={signals.isLoading}
            items={filteredSignals}
            onSelect={handleSelectSignal}
            selectedSymbol={selectedSignal?.symbol ?? ""}
          />
          {isAuthenticated ? (
            <SignalAlertsPanel
              error={signalAlerts.error}
              isLoading={signalAlerts.isLoading}
              items={signalAlerts.items}
              onAcknowledge={(alertId) => signalAlerts.setStatus(alertId, "acknowledged")}
              onMarkRead={(alertId) => signalAlerts.setStatus(alertId, "read")}
              onSelectSymbol={handleSelectSignal}
              selectedWindow={alertWindowMinutes}
              onSelectWindow={setAlertWindowMinutes}
            />
          ) : null}
          <MarketOverviewPanel
            data={marketOverview.data}
            isLoading={marketOverview.isLoading}
            error={marketOverview.error}
          />
          {isAuthenticated ? (
            <IntradayScorecardPanel
              data={scorecard.data}
              error={scorecard.error}
              isLoading={scorecard.isLoading}
              onSelectSignal={handleSelectSignal}
            />
          ) : null}
          <OpportunitiesTable
            items={filteredOpportunities}
            selectedId={selectedOpportunity?.id ?? ""}
            onSelect={handleSelectOpportunity}
            isLoading={opportunities.isLoading}
            error={opportunities.error}
          />
          {isAuthenticated ? (
            <>
              <WatchlistPanel
                data={watchlist.data}
                isLoading={watchlist.isLoading}
                error={watchlist.error}
                actionError={watchlist.actionError}
                isSaving={watchlist.isSaving}
                onAdd={watchlist.addSymbol}
                onRemove={watchlist.removeSymbol}
                suggestedSymbol={suggestedSymbol}
              />
              <PaperTradingPanel
                data={paperTrading.data}
                isLoading={paperTrading.isLoading}
                error={paperTrading.error}
                actionError={paperTrading.actionError}
                isSubmitting={paperTrading.isSubmitting}
                onSubmit={paperTrading.submitOrder}
                suggestedSymbol={suggestedSymbol}
              />
            </>
          ) : (
            <SessionPanel
              actionError={session.actionError}
              isLoading={session.isLoading}
              isSaving={session.isSaving}
              onStartSession={session.startSession}
              session={session.data}
              sessionError={session.error}
            />
          )}
        </section>

        <aside className="sideColumn">
          <SignalInspector
            history={signalHistory.data}
            historyError={signalHistory.error}
            isHistoryLoading={signalHistory.isLoading}
            signal={selectedSignal}
          />
          <RiskPanel
            metrics={risk.data?.metrics ?? []}
            exposures={risk.data?.concentration ?? []}
            isLoading={risk.isLoading}
            error={risk.error}
          />
        </aside>
      </main>
    </div>
  );
}
