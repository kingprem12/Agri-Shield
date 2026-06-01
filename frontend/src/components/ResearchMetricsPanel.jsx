import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { fetchResearchMetrics } from "../services/api.js";

const metricLabels = {
  r2: "R²",
  rmse: "RMSE",
  mae: "MAE",
  mape: "MAPE",
  explained_variance: "Explained Variance",
  accuracy_within_10_vhi: "Accuracy ±10 VHI"
};

export default function ResearchMetricsPanel() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchResearchMetrics().then(setMetrics).catch((caught) => setError(caught.message));
  }, []);

  if (error) {
    return <section className="rounded-3xl bg-red-50 p-6 font-bold text-red-700">{error}</section>;
  }
  if (!metrics) {
    return <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">Loading research metrics...</section>;
  }

  const models = metrics.deep_research.trained_models || [];
  const paperStyle = metrics.paper_style?.metrics || [];
  const gridcellChrono = metrics.gridcell_forecast?.chronological_forecast_metrics || [];
  const gridcellRandom = metrics.gridcell_forecast?.paper_comparable_random_split_metrics || [];
  const paper = metrics.paper;
  const names = models.map((item) => item.model.replace("Real PyTorch ", "").replace("Advanced ", ""));

  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-fuchsia-600">Research Metrics</p>
          <h2 className="text-xl font-black">LSTM vs CNN vs Hybrid</h2>
          <p className="text-sm text-slate-600">Real PyTorch models trained on Sindh grid CSVs; compared against the base paper.</p>
        </div>
        <div className="rounded-2xl bg-amber-50 p-3 text-xs font-semibold text-amber-800">
          Paper: R² {paper.r2}, RMSE {paper.rmse}, MAE {paper.mae}
        </div>
      </div>

      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              <th className="py-2">Model</th>
              {Object.values(metricLabels).map((label) => (
                <th key={label} className="py-2">{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {models.map((model) => (
              <tr key={model.model} className="border-b border-slate-100">
                <td className="max-w-[280px] py-3 font-bold">{model.model}</td>
                {Object.keys(metricLabels).map((key) => (
                  <td key={key} className="py-3">{formatMetric(model[key])}</td>
                ))}
              </tr>
            ))}
            <tr className="bg-amber-50">
              <td className="py-3 font-black">{paper.model}</td>
              <td className="py-3">{paper.r2}</td>
              <td className="py-3">{paper.rmse}</td>
              <td className="py-3">{paper.mae}</td>
              <td className="py-3">—</td>
              <td className="py-3">—</td>
              <td className="py-3">—</td>
            </tr>
          </tbody>
        </table>
      </div>

      <Plot
        data={[
          { x: names, y: models.map((item) => item.r2), name: "R²", type: "bar" },
          { x: names, y: models.map((item) => item.accuracy_within_10_vhi), name: "Accuracy ±10 VHI", type: "bar" }
        ]}
        layout={{
          barmode: "group",
          height: 330,
          margin: { l: 45, r: 20, t: 30, b: 90 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)"
        }}
        useResizeHandler
        className="mt-4 w-full"
      />

      <p className="mt-3 text-xs text-slate-500">
        Important: the paper numbers are reported on its own setup and scale. Do not claim superiority unless the same split, target scaling, and horizon are reproduced.
      </p>

      {(gridcellChrono.length > 0 || gridcellRandom.length > 0) && (
        <div className="mt-8 rounded-2xl border border-blue-200 bg-blue-50 p-5">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Real Grid-Cell Forecast Benchmark</p>
          <h3 className="text-lg font-black">Next-month normalized VHI using real Sindh grid CSVs</h3>
          <p className="mt-1 text-xs text-blue-800">
            This is the strict real forecasting benchmark. It uses real monthly grid cells and predicts next-month VHI.
          </p>
          <MetricTable models={[...gridcellChrono, ...gridcellRandom]} paper={paper} />
        </div>
      )}

      {paperStyle.length > 0 && (
        <div className="mt-8 rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">Paper-Style Benchmark</p>
          <h3 className="text-lg font-black">Normalized same-month VHI estimation</h3>
          <p className="mt-1 text-xs text-emerald-800">
            Separate from future forecasting. This benchmark uses VCI/TCI/VHI-style reconstructed indicators, matching the paper-style task more closely.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-emerald-200 text-emerald-900">
                  <th className="py-2">Model</th>
                  <th className="py-2">R²</th>
                  <th className="py-2">RMSE</th>
                  <th className="py-2">MAE</th>
                  <th className="py-2">MAPE</th>
                  <th className="py-2">Explained Variance</th>
                </tr>
              </thead>
              <tbody>
                {paperStyle.map((model) => (
                  <tr key={model.model} className="border-b border-emerald-100">
                    <td className="py-3 font-bold">{model.model}</td>
                    <td className="py-3">{formatMetric(model.r2)}</td>
                    <td className="py-3">{formatMetric(model.rmse)}</td>
                    <td className="py-3">{formatMetric(model.mae)}</td>
                    <td className="py-3">{formatMetric(model.mape)}</td>
                    <td className="py-3">{formatMetric(model.explained_variance)}</td>
                  </tr>
                ))}
                <tr className="bg-white/70">
                  <td className="py-3 font-black">Base paper Wavelet-XGBoost</td>
                  <td className="py-3">{paper.r2}</td>
                  <td className="py-3">{paper.rmse}</td>
                  <td className="py-3">{paper.mae}</td>
                  <td className="py-3">—</td>
                  <td className="py-3">—</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

function MetricTable({ models, paper }) {
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full min-w-[760px] text-left text-sm">
        <thead>
          <tr className="border-b border-blue-200 text-blue-900">
            <th className="py-2">Model</th>
            <th className="py-2">R²</th>
            <th className="py-2">RMSE</th>
            <th className="py-2">MAE</th>
            <th className="py-2">MAPE</th>
            <th className="py-2">Explained Var.</th>
            <th className="py-2">Acc ±0.10 VHI</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.model} className="border-b border-blue-100">
              <td className="py-3 font-bold">{model.model}</td>
              <td className="py-3">{formatMetric(model.r2)}</td>
              <td className="py-3">{formatMetric(model.rmse)}</td>
              <td className="py-3">{formatMetric(model.mae)}</td>
              <td className="py-3">{formatMetric(model.mape)}</td>
              <td className="py-3">{formatMetric(model.explained_variance)}</td>
              <td className="py-3">{formatMetric(model.accuracy_within_0_10_vhi)}</td>
            </tr>
          ))}
          <tr className="bg-white/70">
            <td className="py-3 font-black">Base paper Wavelet-XGBoost</td>
            <td className="py-3">{paper.r2}</td>
            <td className="py-3">{paper.rmse}</td>
            <td className="py-3">{paper.mae}</td>
            <td className="py-3">—</td>
            <td className="py-3">—</td>
            <td className="py-3">—</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function formatMetric(value) {
  if (value === undefined || value === null) return "—";
  return Number(value).toFixed(3);
}
