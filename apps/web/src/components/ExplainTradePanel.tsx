import { useEffect, useState } from "react";
import { getTradeExplanation, toErrorMessage } from "../lib/api";
import type { TradeExplanationResponse } from "../lib/contracts";

interface ExplainTradePanelProps {
  tradeId: string;
}

export function ExplainTradePanel({ tradeId }: ExplainTradePanelProps) {
  const [explanation, setExplanation] = useState<TradeExplanationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    setIsLoading(true);
    setError(null);

    getTradeExplanation(tradeId, controller.signal)
      .then((response) => {
        setExplanation(response);
        setIsLoading(false);
      })
      .catch((requestError: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        setError(toErrorMessage(requestError));
        setIsLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [tradeId]);

  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Explain this trade</p>
          <h2>Model rationale</h2>
        </div>
      </div>

      {isLoading ? (
        <div className="stateBlock">
          <strong>Loading explanation...</strong>
          <p>The explanation service is preparing a structured rationale for this setup.</p>
        </div>
      ) : null}

      {!isLoading && error ? (
        <div className="stateBlock isError">
          <strong>Explanation unavailable.</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {!isLoading && !error && explanation ? (
        <>
          <p className="detailCopy">{explanation.summary}</p>

          <div className="sectionSubheader">
            <p className="eyebrow">Top drivers</p>
          </div>
          <div className="explanationList">
            {explanation.drivers.map((driver) => (
              <div
                key={driver.title}
                className="infoCard"
              >
                <strong>{driver.title}</strong>
                <p>{driver.detail}</p>
              </div>
            ))}
          </div>

          <div className="sectionSubheader">
            <p className="eyebrow">Warnings</p>
          </div>
          <div className="warningList">
            {explanation.warnings.map((warning) => (
              <div
                key={`${warning.severity}-${warning.title}`}
                className="warningItem"
              >
                <span className={`warningTag is${warning.severity}`}>
                  {warning.severity}
                </span>
                <div>
                  <strong>{warning.title}</strong>
                  <p>{warning.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
