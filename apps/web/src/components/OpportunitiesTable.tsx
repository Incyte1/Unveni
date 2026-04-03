import type { Opportunity } from "../data/mock";

interface OpportunitiesTableProps {
  items: Opportunity[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function OpportunitiesTable({
  items,
  selectedId,
  onSelect
}: OpportunitiesTableProps) {
  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Ranked candidates</p>
          <h2>Opportunities</h2>
        </div>
        <p className="sectionMeta">
          Learning-to-rank output after liquidity, slippage, and ES gates.
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
            {items.length === 0 ? (
              <tr className="isEmpty">
                <td colSpan={6}>
                  <div className="tradeCell">
                    <strong>No opportunities match the current filter set.</strong>
                    <span>Try a broader symbol search or switch back to all strategy templates.</span>
                  </div>
                </td>
              </tr>
            ) : null}
            {items.map((item, index) => {
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
                      {item.expectedReturn.toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <span className="mono negative">
                      {item.expectedShortfall.toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <span className="mono">{item.winRate}%</span>
                  </td>
                  <td>
                    <span className="mono">{item.spreadBps} bps</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
