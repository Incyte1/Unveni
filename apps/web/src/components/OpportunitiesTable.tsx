import type { OpportunityRecord } from "../lib/contracts";

interface OpportunitiesTableProps {
  items: OpportunityRecord[];
  selectedId: string;
  onSelect: (id: string) => void;
  isLoading: boolean;
  error: string | null;
}

export function OpportunitiesTable({
  items,
  selectedId,
  onSelect,
  isLoading,
  error
}: OpportunitiesTableProps) {
  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Supporting feed</p>
          <h2>Opportunity context</h2>
        </div>
        <p className="sectionMeta">
          Legacy research context stays on the dashboard, but the intraday signal engine no longer depends on this feed.
        </p>
      </div>
      <div className="tableWrap">
        <table className="opportunitiesTable">
          <thead>
            <tr>
              <th>Trade</th>
              <th>Score</th>
              <th>Exp. return</th>
              <th>ES</th>
              <th>Win rate</th>
              <th>Spread</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr className="isEmpty">
                <td colSpan={6}>
                  <div className="tradeCell">
                    <strong>Loading ranked opportunities...</strong>
                    <span>The dashboard is waiting for the opportunities feed.</span>
                  </div>
                </td>
              </tr>
            ) : null}
            {!isLoading && error ? (
              <tr className="isEmpty">
                <td colSpan={6}>
                  <div className="tradeCell">
                    <strong>Opportunity feed unavailable.</strong>
                    <span>{error}</span>
                  </div>
                </td>
              </tr>
            ) : null}
            {!isLoading && !error && items.length === 0 ? (
              <tr className="isEmpty">
                <td colSpan={6}>
                  <div className="tradeCell">
                    <strong>No opportunities match the current filter set.</strong>
                    <span>Try a broader symbol search or switch back to all strategy templates.</span>
                  </div>
                </td>
              </tr>
            ) : null}
            {!isLoading && !error
              ? items.map((item, index) => {
                  const active = item.id === selectedId;

                  return (
                    <tr
                      key={item.id}
                      className={active ? "isActive" : undefined}
                      tabIndex={0}
                      onClick={() => onSelect(item.id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelect(item.id);
                        }
                      }}
                      style={{ animationDelay: `${index * 55}ms` }}
                    >
                      <td>
                        <div className="tradeCell">
                          <strong>
                            {item.symbol} {item.structure}
                          </strong>
                          <span>{item.thesis}</span>
                          <div className="tagRow">
                            {item.catalysts.slice(0, 2).map((catalyst) => (
                              <span
                                key={catalyst}
                                className="tag"
                              >
                                {catalyst}
                              </span>
                            ))}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="mono score">{item.score}</span>
                      </td>
                      <td>
                        <span className="mono positive">
                          {item.expected_return.toFixed(1)}%
                        </span>
                      </td>
                      <td>
                        <span className="mono negative">
                          {item.expected_shortfall.toFixed(1)}%
                        </span>
                      </td>
                      <td>
                        <span className="mono">{item.win_rate}%</span>
                      </td>
                      <td>
                        <span className="mono">{item.spread_bps} bps</span>
                      </td>
                    </tr>
                  );
                })
              : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
