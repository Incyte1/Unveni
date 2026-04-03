import { startTransition, useDeferredValue, useEffect, useState } from "react";
import { BacktestPanel } from "./components/BacktestPanel";
import { Header } from "./components/Header";
import { OpportunitiesTable } from "./components/OpportunitiesTable";
import { RiskPanel } from "./components/RiskPanel";
import { TradeDetailDrawer } from "./components/TradeDetailDrawer";
import {
  backtest,
  exposureBuckets,
  opportunities,
  riskMetrics,
  strategyFilters,
  type StrategyType
} from "./data/mock";

type StrategyFilter = StrategyType | "All";

export default function App() {
  const [query, setQuery] = useState("");
  const [strategy, setStrategy] = useState<StrategyFilter>("All");
  const [selectedId, setSelectedId] = useState(opportunities[0].id);
  const deferredQuery = useDeferredValue(query);

  const filtered = opportunities.filter((item) => {
    const matchesQuery =
      item.symbol.toLowerCase().includes(deferredQuery.toLowerCase()) ||
      item.structure.toLowerCase().includes(deferredQuery.toLowerCase()) ||
      item.thesis.toLowerCase().includes(deferredQuery.toLowerCase());
    const matchesStrategy = strategy === "All" || item.structure === strategy;

    return matchesQuery && matchesStrategy;
  });

  useEffect(() => {
    if (!filtered.some((item) => item.id === selectedId) && filtered.length > 0) {
      setSelectedId(filtered[0].id);
    }
  }, [filtered, selectedId]);

  const selected = filtered.find((item) => item.id === selectedId) ?? filtered[0];

  return (
    <div className="appShell">
      <Header opportunityCount={filtered.length} />

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
            <p className="eyebrow">Templates</p>
          </div>
          <div className="filterList">
            {strategyFilters.map((option) => (
              <button
                key={option}
                type="button"
                className={option === strategy ? "filterChip isSelected" : "filterChip"}
                onClick={() => {
                  startTransition(() => {
                    setStrategy(option);
                  });
                }}
              >
                {option}
              </button>
            ))}
          </div>

          <div className="sectionSubheader">
            <p className="eyebrow">Model stack</p>
          </div>
          <ul className="plainList">
            <li>TFT or regime forecasters feed candidate priors.</li>
            <li>LightGBM LambdaRank selects top tradable structures.</li>
            <li>Runtime gates enforce delta, vega, ES, and concentration caps.</li>
          </ul>

          <div className="callout">
            Data posture: public UI stays on delayed analytics until market-data entitlements are attached to the user session.
          </div>
        </aside>

        <section className="mainColumn">
          <OpportunitiesTable
            items={filtered}
            selectedId={selected?.id ?? ""}
            onSelect={setSelectedId}
          />
          <BacktestPanel series={backtest} />
        </section>

        <aside className="sideColumn">
          {selected ? (
            <TradeDetailDrawer item={selected} />
          ) : (
            <section className="panel reveal">
              <div className="sectionHeader">
                <div>
                  <p className="eyebrow">Selected trade</p>
                  <h2>No matches</h2>
                </div>
              </div>
              <p className="detailCopy">
                Expand the search or clear a template filter to restore candidate trades.
              </p>
            </section>
          )}
          <RiskPanel
            metrics={riskMetrics}
            exposures={exposureBuckets}
          />
        </aside>
      </main>
    </div>
  );
}
