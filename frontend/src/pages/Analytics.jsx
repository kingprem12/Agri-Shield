import RiskChart from "../components/RiskChart.jsx";
import ResearchMetricsPanel from "../components/ResearchMetricsPanel.jsx";

export default function Analytics({ history }) {
  const severityCounts = history.reduce((acc, item) => {
    acc[item.severity] = (acc[item.severity] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
      <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h2 className="text-xl font-bold">Analytics</h2>
        <p className="mt-2 text-slate-600">Prediction history, risk distribution, and drought alert monitoring.</p>
        <RiskChart history={history} />
      </section>
      <ResearchMetricsPanel />
      <section className="grid gap-4 md:grid-cols-3">
        {Object.entries(severityCounts).map(([severity, count]) => (
          <div key={severity} className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p className="font-bold">{severity}</p>
            <p className="text-3xl font-black">{count}</p>
          </div>
        ))}
      </section>
      <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h3 className="text-lg font-bold">Recent crop suggestions</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {history.slice(0, 6).map((item) => (
            <div key={item.id} className="rounded-2xl bg-slate-50 p-4">
              <p className="font-bold">{item.district}, {item.state}</p>
              <p className="text-sm text-slate-600">{item.severity}</p>
              <p className="mt-2 text-sm font-semibold text-emerald-700">
                {(item.suitable_crops || []).join(", ") || "Run a new prediction to generate crop suggestions."}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
