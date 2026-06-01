import IndiaMap from "../components/IndiaMap.jsx";
import ForecastPanel from "../components/ForecastPanel.jsx";
import PredictionForm from "../components/PredictionForm.jsx";
import RiskChart from "../components/RiskChart.jsx";

export default function Dashboard({ history, onPrediction }) {
  const highRisk = history.filter((item) => item.risk_score >= 55).length;
  const latest = history[0];
  const averageRisk = history.length
    ? history.reduce((total, item) => total + item.risk_score, 0) / history.length
    : 0;
  return (
    <div className="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[1.3fr_0.9fr]">
      <section className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-4">
          <Card label="Predictions" value={history.length} />
          <Card label="High Risk Alerts" value={highRisk} />
          <Card label="Average Risk" value={history.length ? averageRisk.toFixed(1) : "—"} />
          <Card label="Latest Severity" value={latest?.severity || "No data"} />
        </div>
        {latest && (
          <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-5">
            <p className="text-sm font-bold uppercase tracking-wide text-emerald-700">Latest dashboard update</p>
            <p className="mt-1 text-xl font-black text-slate-950">
              {latest.district}, {latest.state}: {latest.severity} · {Number(latest.risk_score).toFixed(1)} risk
            </p>
          </div>
        )}
        <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-4 text-lg font-bold">Interactive India Risk Map</h2>
          <IndiaMap history={history} />
        </div>
        <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <h2 className="text-lg font-bold">Recent Risk Trend</h2>
          <RiskChart history={history} />
        </div>
        <ForecastPanel />
      </section>
      <PredictionForm onPrediction={onPrediction} />
    </div>
  );
}

function Card({ label, value }) {
  return (
    <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <p className="text-sm font-semibold text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-black text-slate-950">{value}</p>
    </div>
  );
}
