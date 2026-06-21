import { useEffect, useMemo, useState } from "react";
import { fetchResearchResults } from "../services/api.js";

const fallbackResults = {
  dataset_rows: 1361299,
  dataset_columns: 43,
  grid_cells: 4937,
  study_period: "2001-2023",
  date_range: "2001-01 to 2023-12",
  region: "Sindh",
  target: "vhi_next_month",
  model: "PSO-Optimized LightGBM Strict Future Forecaster",
  r2: 0.8153,
  rmse: 0.1097,
  mae: 0.0839,
  f1: 0.6354,
  top_features: [
    "modis_ndvi__t-0",
    "vci_lag_1__t-0",
    "evi__t-0",
    "vhi_wavelet_approx__t-10",
    "spei_6__t-0",
    "vhi_lag_12__t-11",
    "spei_12__t-0",
    "solar_radiation__t-0"
  ],
  honesty_note:
    "This is strict next-month forecasting using real GEE data. Same-month estimation is reported separately and is not used as the main future forecasting claim."
};

export default function ResearchResults() {
  const [results, setResults] = useState(fallbackResults);
  const [source, setSource] = useState("local verified metrics");

  useEffect(() => {
    fetchResearchResults()
      .then((data) => {
        setResults({ ...fallbackResults, ...data });
        setSource("backend API");
      })
      .catch(() => {
        setResults(fallbackResults);
        setSource("local verified metrics");
      });
  }, []);

  const metrics = useMemo(
    () => [
      { label: "R2", value: results.r2, text: "Higher is better", tone: "emerald" },
      { label: "RMSE", value: results.rmse, text: "Lower is better", tone: "amber" },
      { label: "MAE", value: results.mae, text: "Lower is better", tone: "amber" },
      { label: "F1", value: results.f1, text: "Higher is better", tone: "emerald" }
    ],
    [results]
  );

  const summary = [
    ["Dataset", `${Number(results.dataset_rows).toLocaleString()} rows`],
    ["Grid Cells", Number(results.grid_cells).toLocaleString()],
    ["Study Period", results.study_period],
    ["Region", results.region]
  ];

  return (
    <div className="research-shell">
      <section className="research-hero">
        <div>
          <p className="research-kicker">Research Results</p>
          <h2>Strict Future Drought Forecasting for Sindh</h2>
          <p>
            AgriShield-X predicts next-month VHI with enriched Google Earth Engine climate and vegetation features,
            using a PSO-optimized LightGBM strict forecasting model.
          </p>
        </div>
        <div className="research-hero-card">
          <span>Production candidate</span>
          <strong>{results.model}</strong>
          <small>Data source: {source}</small>
        </div>
      </section>

      <section className="research-grid research-grid-four">
        {summary.map(([label, value]) => (
          <ClayCard key={label}>
            <p className="research-card-label">{label}</p>
            <strong className="research-card-value">{value}</strong>
          </ClayCard>
        ))}
      </section>

      <section className="research-grid research-grid-four">
        {metrics.map((metric) => (
          <ClayCard key={metric.label} accent={metric.tone}>
            <p className="research-card-label">{metric.label}</p>
            <strong className="research-metric">{Number(metric.value).toFixed(4)}</strong>
            <span className="research-card-note">{metric.text}</span>
          </ClayCard>
        ))}
      </section>

      <section className="research-two-column">
        <ClayCard>
          <h3>Model Overview</h3>
          <p>
            The model uses only information available through month t to predict {results.target} at month t+1.
            It combines seasonal signals, spatial context, rolling climate summaries, vegetation indices, and solar
            radiation signals in a strict chronological validation protocol.
          </p>
        </ClayCard>
        <ClayCard>
          <h3>Dataset Summary</h3>
          <dl className="research-definition">
            <div><dt>Rows</dt><dd>{Number(results.dataset_rows).toLocaleString()}</dd></div>
            <div><dt>Columns</dt><dd>{results.dataset_columns}</dd></div>
            <div><dt>Grid cells</dt><dd>{Number(results.grid_cells).toLocaleString()}</dd></div>
            <div><dt>Date range</dt><dd>{results.date_range}</dd></div>
            <div><dt>Target</dt><dd>{results.target}</dd></div>
          </dl>
        </ClayCard>
      </section>

      <section className="research-two-column">
        <ClayCard>
          <h3>Metrics Explanation</h3>
          <ul className="research-list">
            <li>Higher R2 means the model explains more next-month VHI variation.</li>
            <li>Lower RMSE means fewer large forecasting errors.</li>
            <li>Lower MAE means smaller average absolute forecast error.</li>
            <li>Higher F1 means drought severity classes are detected more reliably.</li>
          </ul>
        </ClayCard>
        <ClayCard>
          <h3>Top Features</h3>
          <div className="feature-pills">
            {results.top_features.map((feature) => (
              <span key={feature}>{feature}</span>
            ))}
          </div>
        </ClayCard>
      </section>

      <section className="research-two-column">
        <ClayCard>
          <h3>Farmer Benefit</h3>
          <ul className="research-list">
            <li>Early drought warning before the next month arrives.</li>
            <li>Better irrigation planning when rainfall and heat stress signals rise.</li>
            <li>Crop selection support for water-sensitive growing periods.</li>
            <li>Risk-based farming decisions grounded in real satellite and climate data.</li>
          </ul>
        </ClayCard>
        <ClayCard accent="earth">
          <h3>Research Honesty Note</h3>
          <p>{results.honesty_note}</p>
        </ClayCard>
      </section>
    </div>
  );
}

function ClayCard({ children, accent = "green" }) {
  return <div className={`clay-card clay-card-${accent}`}>{children}</div>;
}
