import { useEffect, useMemo, useState } from "react";
import {
  fetchPsoSindhFeatureImportance,
  fetchPsoSindhMetrics,
  fetchPsoFutureMetrics,
  predictPsoSindh
} from "../services/api.js";

const basePaper = { r2: 0.964, rmse: 0.021, mae: 0.023 };

export default function SindhPso() {
  const [report, setReport] = useState(null);
  const [futureReport, setFutureReport] = useState(null);
  const [importance, setImportance] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    latitude: 26,
    longitude: 68.5,
    month: 6,
    year: 2026,
    ndvi: 0.35,
    lst: 38,
    rainfall: 20,
    temperature: 36,
    humidity: 35,
    soil_moisture: 0.18
  });

  useEffect(() => {
    async function load() {
      try {
        const [metrics, features] = await Promise.all([
          fetchPsoSindhMetrics(),
          fetchPsoSindhFeatureImportance()
        ]);
        setReport(metrics);
        setImportance(features.features || []);
        fetchPsoFutureMetrics().then(setFutureReport).catch(() => setFutureReport(null));
      } catch (err) {
        setError(err.message);
      }
    }
    load();
  }, []);

  const protocols = report?.protocols || {};
  const best = report?.best_model || protocols.A_strict_chronological_future_forecasting || {};
  const samples = report?.actual_vs_predicted_sample || [];
  const conclusion = report?.claim || "PSO Sindh model has not been trained yet.";

  const cards = useMemo(
    () => [
      ["R2", best.r2],
      ["RMSE", best.rmse],
      ["MAE", best.mae],
      ["MAPE", best.mape]
    ],
    [best]
  );

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      setPrediction(await predictPsoSindh(form));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
      <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <p className="text-sm font-bold uppercase tracking-wide text-emerald-700">Sindh PSO Drought Intelligence</p>
        <h2 className="mt-2 text-3xl font-black text-slate-950">PSO-Optimized Wavelet-XGBoost</h2>
        <p className="mt-3 max-w-3xl text-slate-600">
          Dedicated Sindh agricultural drought model using GEE remote sensing time-series features, causal lag and rolling windows,
          wavelet decomposition, and Particle Swarm Optimization for XGBoost hyperparameters and feature subset selection.
        </p>
      </section>

      {error && <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 font-semibold text-rose-700">{error}</div>}

      <FutureForecastingPanel report={futureReport} />

      <section className="grid gap-4 md:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="text-sm font-semibold text-slate-500">{label}</p>
            <p className="mt-2 text-3xl font-black text-slate-950">{typeof value === "number" ? value.toFixed(4) : "—"}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_0.85fr]">
        <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h3 className="text-xl font-bold">Base paper vs PSO model</h3>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-slate-500">
                <tr><th>Protocol</th><th>R2</th><th>RMSE</th><th>MAE</th><th>MAPE</th></tr>
              </thead>
              <tbody>
                <tr className="border-t"><td>Base paper</td><td>{basePaper.r2}</td><td>{basePaper.rmse}</td><td>{basePaper.mae}</td><td>—</td></tr>
                {Object.values(protocols).map((row) => (
                  <tr key={row.protocol} className="border-t">
                    <td className="py-2 font-semibold">{row.protocol.replaceAll("_", " ")}</td>
                    <td>{row.r2?.toFixed(4)}</td>
                    <td>{row.rmse?.toFixed(4)}</td>
                    <td>{row.mae?.toFixed(4)}</td>
                    <td>{row.mape?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <form onSubmit={submit} className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h3 className="text-xl font-bold">Prediction form</h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {Object.entries(form).map(([key, value]) => (
              <label key={key} className="text-sm font-semibold text-slate-600">
                {key.replaceAll("_", " ")}
                <input
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-slate-950"
                  type="number"
                  step="any"
                  value={value}
                  onChange={(event) => setForm((current) => ({ ...current, [key]: Number(event.target.value) }))}
                />
              </label>
            ))}
          </div>
          <button className="mt-4 w-full rounded-2xl bg-emerald-600 px-4 py-3 font-bold text-white">Predict Sindh drought severity</button>
          {prediction && (
            <div className="mt-4 rounded-2xl bg-emerald-50 p-4">
              <p className="text-sm font-bold text-emerald-700">Drought severity output</p>
              <p className="mt-1 text-2xl font-black text-slate-950">{prediction.drought_severity}</p>
              <p className="text-sm text-slate-600">Predicted VHI {prediction.predicted_vhi.toFixed(4)} · Risk {prediction.risk_score.toFixed(1)}</p>
            </div>
          )}
        </form>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Actual vs predicted chart">
          <ActualPredicted points={samples} />
        </ChartCard>
        <ChartCard title="Feature importance chart">
          <FeatureBars features={importance} />
        </ChartCard>
      </section>

      <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5">
        <p className="font-bold text-amber-800">Protocol warning</p>
        <p className="mt-1 text-sm text-amber-800">Strict forecasting and same-month estimation are reported separately. Same-month estimation is not future forecasting.</p>
      </section>

      <section className="rounded-3xl bg-slate-950 p-6 text-white">
        <p className="text-sm font-bold uppercase tracking-wide text-emerald-300">Research conclusion</p>
        <p className="mt-2 text-2xl font-black">{conclusion}</p>
        <p className="mt-3 text-sm text-slate-300">
          Dataset: {report?.dataset?.source || "Existing local Sindh GEE remote sensing CSV files"} · {report?.dataset?.rows || "—"} rows · {report?.dataset?.csv_files || "—"} monthly CSV files.
        </p>
      </section>
    </div>
  );
}

function FutureForecastingPanel({ report }) {
  const strict = report?.protocols?.A_strict_chronological_next_month_forecasting || {};
  const rolling = report?.protocols?.E_rolling_origin_validation || {};
  const spatial = report?.protocols?.D_spatial_holdout_secondary || {};
  return (
    <section className="rounded-3xl border border-blue-200 bg-blue-50 p-6">
      <p className="text-sm font-bold uppercase tracking-wide text-blue-700">True Future Forecasting Result</p>
      <h3 className="mt-2 text-2xl font-black text-slate-950">PSO Wavelet-Lag ExtraTrees + XGBoost Ensemble</h3>
      <p className="mt-2 max-w-3xl text-sm text-blue-900">
        Strict next-month forecasting only. The feature window ends at month t and predicts VHI at month t+1; target-month VHI, VCI, and TCI are not used.
      </p>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        {[
          ["Strict R2", strict.r2],
          ["Strict RMSE", strict.rmse],
          ["Strict MAE", strict.mae],
          ["Severity F1", strict.drought_severity_f1]
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl bg-white p-4 ring-1 ring-blue-100">
            <p className="text-xs font-bold text-slate-500">{label}</p>
            <p className="mt-1 text-2xl font-black text-slate-950">{typeof value === "number" ? value.toFixed(4) : "—"}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-blue-800">
            <tr><th>Protocol</th><th>R2</th><th>RMSE</th><th>MAE</th><th>F1</th></tr>
          </thead>
          <tbody>
            {[
              ["Strict chronological", strict],
              ["Rolling origin", rolling],
              ["Spatial holdout", spatial]
            ].map(([label, row]) => (
              <tr key={label} className="border-t border-blue-100">
                <td className="py-2 font-semibold">{label}</td>
                <td>{row.r2?.toFixed?.(4) || "—"}</td>
                <td>{row.rmse?.toFixed?.(4) || "—"}</td>
                <td>{row.mae?.toFixed?.(4) || "—"}</td>
                <td>{row.drought_severity_f1?.toFixed?.(4) || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-sm font-semibold text-blue-900">{report?.claim || "Strict future forecasting model has not been trained yet."}</p>
    </section>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <h3 className="text-xl font-bold">{title}</h3>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function ActualPredicted({ points }) {
  if (!points.length) return <p className="text-sm text-slate-500">No prediction sample available yet.</p>;
  return (
    <div className="h-64">
      <svg viewBox="0 0 320 180" className="h-full w-full">
        <line x1="28" y1="150" x2="300" y2="150" stroke="#cbd5e1" />
        <line x1="28" y1="20" x2="28" y2="150" stroke="#cbd5e1" />
        <polyline fill="none" stroke="#059669" strokeWidth="2" points={toPolyline(points, "actual")} />
        <polyline fill="none" stroke="#2563eb" strokeWidth="2" points={toPolyline(points, "predicted")} />
      </svg>
      <div className="flex gap-4 text-sm font-semibold"><span className="text-emerald-700">Actual</span><span className="text-blue-700">Predicted</span></div>
    </div>
  );
}

function FeatureBars({ features }) {
  if (!features.length) return <p className="text-sm text-slate-500">No feature importance available yet.</p>;
  const maxValue = Math.max(...features.map((item) => item.importance), 1e-6);
  return (
    <div className="space-y-2">
      {features.slice(0, 12).map((item) => (
        <div key={item.feature}>
          <div className="mb-1 flex justify-between text-xs font-semibold text-slate-600"><span>{item.feature}</span><span>{item.importance.toFixed(3)}</span></div>
          <div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-emerald-500" style={{ width: `${(item.importance / maxValue) * 100}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

function toPolyline(points, key) {
  return points
    .map((point, index) => {
      const x = 28 + (index / Math.max(points.length - 1, 1)) * 272;
      const y = 150 - Math.max(0, Math.min(1, point[key])) * 130;
      return `${x},${y}`;
    })
    .join(" ");
}
