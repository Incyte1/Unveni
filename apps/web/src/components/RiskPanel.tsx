import type { ExposureBucket, RiskMetric } from "../data/mock";

interface RiskPanelProps {
  metrics: RiskMetric[];
  exposures: ExposureBucket[];
}

export function RiskPanel({ metrics, exposures }: RiskPanelProps) {
  return (
    <section className="panel reveal">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Hard controls</p>
          <h2>Risk panel</h2>
        </div>
      </div>

      <div className="metricStack">
        {metrics.map((metric) => {
          const utilization = Math.min(
            100,
            Math.round((metric.current / metric.limit) * 100)
          );

          return (
            <div
              key={metric.label}
              className="metricRow"
            >
              <div className="metricLabelRow">
                <span>{metric.label}</span>
                <span className="mono">
                  {metric.current}
                  {metric.unit} / {metric.limit}
                  {metric.unit}
                </span>
              </div>
              <div
                className="meter"
                aria-hidden="true"
              >
                <span
                  style={{ width: `${utilization}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="sectionSubheader">
        <p className="eyebrow">Expiry concentration</p>
      </div>
      <div className="bucketList">
        {exposures.map((bucket) => (
          <div
            key={bucket.label}
            className="bucketRow"
          >
            <span>{bucket.label}</span>
            <strong className="mono">{bucket.value}%</strong>
          </div>
        ))}
      </div>

      <div className="callout">
        Kill switch: reject any basket breaching ES 3.0%, vega 0.35, or single-name concentration 25%.
      </div>
    </section>
  );
}
