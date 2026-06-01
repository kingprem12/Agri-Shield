import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import { fetchBenchmark } from "../services/api.js";

const protocolLabels = {
  A_strict_chronological_next_month: "Strict Future Forecasting",
  B_paper_comparable_random_split: "Paper-Comparable Random Split",
  C_same_month_vhi_estimation: "Same-Month Estimation",
  D_spatial_grid_cell_holdout: "Spatial Grid Holdout"
};

export default function BenchmarkPanel() {
  const [benchmark, setBenchmark] = useState(null);
  const [selectedProtocol, setSelectedProtocol] = useState("A_strict_chronological_next_month");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchBenchmark().then(setBenchmark).catch((caught) => setError(caught.message));
  }, []);

  const deepHybrid = benchmark?.reports?.deep_hybrid || benchmark?.reports?.deep_hybrid_smoke;
  const rows = useMemo(() => deepHybrid?.protocols?.[selectedProtocol] || [], [deepHybrid, selectedProtocol]);

  if (error) {
    return <section className="rounded-lg bg-red-50 p-5 font-bold text-red-700">{error}</section>;
  }
  if (!benchmark) {
    return <section className="rounded-lg bg-white p-5 shadow-sm ring-1 ring-slate-200">Loading benchmark...</section>;
  }

  const best = deepHybrid?.best_model;
  const beatMetrics = Object.entries(deepHybrid?.success_against_base_paper || {})
    .filter(([, value]) => value)
    .map(([key]) => key.toUpperCase());

  return (
    <section className="space-y-5">
      <div className="rounded-lg bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-emerald-700">Deep Hybrid Benchmark</p>
            <h2 className="text-xl font-black text-slate-950">Honest protocol comparison</h2>
            <p className="mt-1 text-sm text-slate-600">
              Base paper: R² {benchmark.base_paper.r2}, RMSE {benchmark.base_paper.rmse}, MAE {benchmark.base_paper.mae}
            </p>
          </div>
          <div className="rounded-lg bg-amber-50 p-3 text-sm font-bold text-amber-800">
            {beatMetrics.length ? `Beat base paper on: ${beatMetrics.join(", ")}` : "No base-paper metric beaten"}
          </div>
        </div>
        {best && (
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <Metric label="Best Model" value={best.model} />
            <Metric label="Protocol" value={protocolLabels[best.protocol] || best.protocol} />
            <Metric label="R²" value={format(best.r2)} />
            <Metric label="RMSE / MAE" value={`${format(best.rmse)} / ${format(best.mae)}`} />
          </div>
        )}
        <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm font-semibold text-slate-700">
          {deepHybrid?.claim || benchmark.warning}
        </p>
      </div>

      <div className="rounded-lg bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div className="flex flex-wrap gap-2">
          {Object.keys(protocolLabels).map((protocol) => (
            <button
              key={protocol}
              onClick={() => setSelectedProtocol(protocol)}
              className={`rounded-lg px-3 py-2 text-sm font-bold ${
                selectedProtocol === protocol ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-700"
              }`}
            >
              {protocolLabels[protocol]}
            </button>
          ))}
        </div>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2">Model</th>
                <th className="py-2">R²</th>
                <th className="py-2">RMSE</th>
                <th className="py-2">MAE</th>
                <th className="py-2">MAPE</th>
                <th className="py-2">Explained Var.</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.model} className="border-b border-slate-100">
                  <td className="max-w-[340px] py-3 font-bold">{row.model}</td>
                  <td className="py-3">{format(row.r2)}</td>
                  <td className="py-3">{format(row.rmse)}</td>
                  <td className="py-3">{format(row.mae)}</td>
                  <td className="py-3">{format(row.mape)}</td>
                  <td className="py-3">{format(row.explained_variance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length > 0 && (
          <Plot
            data={[
              { x: rows.map((row) => row.model), y: rows.map((row) => row.r2), name: "R²", type: "bar" },
              { x: rows.map((row) => row.model), y: rows.map((row) => row.rmse), name: "RMSE", type: "bar" }
            ]}
            layout={{
              barmode: "group",
              height: 360,
              margin: { l: 45, r: 20, t: 20, b: 130 },
              paper_bgcolor: "rgba(0,0,0,0)",
              plot_bgcolor: "rgba(0,0,0,0)"
            }}
            useResizeHandler
            className="mt-4 w-full"
          />
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-black text-slate-950">{value}</p>
    </div>
  );
}

function format(value) {
  if (value === undefined || value === null) return "-";
  return Number(value).toFixed(3);
}
