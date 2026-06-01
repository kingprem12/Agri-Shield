import { useState } from "react";
import Plot from "react-plotly.js";
import { REGIONS } from "../data/regions.js";
import { explainForecast, forecastVhi } from "../services/api.js";

function regionPayload(region, horizonMonths) {
  return {
    region: `${region.district}, ${region.state}`,
    horizon_months: horizonMonths,
    date: "2023-12",
    ndvi: region.ndvi,
    lst: region.lst,
    rainfall: region.rainfall,
    temperature: region.temperature,
    humidity: region.humidity,
    solar_radiation: 24 + region.lst * 0.2,
    wind_speed: region.wind_speed,
    soil_moisture: region.soil_moisture_proxy
  };
}

export default function ForecastPanel() {
  const [selectedLabel, setSelectedLabel] = useState("Jodhpur, Rajasthan");
  const [horizonMonths, setHorizonMonths] = useState(3);
  const [forecast, setForecast] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function runForecast() {
    const region = REGIONS.find((item) => item.label === selectedLabel) || REGIONS[0];
    const payload = regionPayload(region, horizonMonths);
    setLoading(true);
    setError("");
    try {
      const result = await forecastVhi(payload);
      const xai = await explainForecast(payload);
      setForecast(result);
      setExplanation(xai);
    } catch (caught) {
      setError(caught.message || "Forecast failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">AgriShield-X</p>
          <h2 className="text-xl font-black">Future VHI Forecast</h2>
          <p className="text-sm text-slate-600">Forecasts future Vegetation Health Index and drought severity.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={selectedLabel}
            onChange={(event) => setSelectedLabel(event.target.value)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold"
          >
            {REGIONS.map((region) => (
              <option key={region.label}>{region.label}</option>
            ))}
          </select>
          <select
            value={horizonMonths}
            onChange={(event) => setHorizonMonths(Number(event.target.value))}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold"
          >
            {[1, 3, 6, 12].map((months) => (
              <option key={months} value={months}>{months} month forecast</option>
            ))}
          </select>
          <button onClick={runForecast} className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white">
            {loading ? "Forecasting..." : "Run Forecast"}
          </button>
        </div>
      </div>
      {error && <div className="mt-4 rounded-2xl bg-red-50 p-4 text-sm font-bold text-red-700">{error}</div>}
      {forecast && (
        <div className="mt-5 grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl bg-slate-50 p-4">
            <Plot
              data={[
                {
                  x: forecast.forecasts.map((item) => item.date),
                  y: forecast.forecasts.map((item) => item.forecast_vhi),
                  type: "scatter",
                  mode: "lines+markers",
                  marker: { color: "#4f46e5" },
                  line: { width: 4 }
                }
              ]}
              layout={{
                height: 320,
                margin: { l: 45, r: 20, t: 20, b: 40 },
                yaxis: { title: "Forecast VHI", range: [0, 100] },
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)"
              }}
              useResizeHandler
              className="w-full"
            />
          </div>
          <div className="space-y-3">
            {forecast.forecasts.map((item) => (
              <div key={item.date} className="rounded-2xl border border-slate-200 p-4">
                <p className="text-sm font-bold text-slate-500">{item.date}</p>
                <p className="text-2xl font-black">{item.severity}</p>
                <p className="text-sm text-slate-600">VHI {item.forecast_vhi} · confidence {(item.confidence * 100).toFixed(0)}%</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {explanation && (
        <div className="mt-5 rounded-2xl bg-indigo-50 p-4">
          <p className="text-sm font-black text-indigo-700">Explainable AI feature importance</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {explanation.global_top_features.map((item) => (
              <span key={item.feature} className="rounded-full bg-white px-3 py-1 text-xs font-bold text-indigo-700 ring-1 ring-indigo-200">
                {item.feature}: {(item.importance * 100).toFixed(1)}%
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
