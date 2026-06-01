import { useState } from "react";
import { REGIONS } from "../data/regions.js";
import { predictDrought } from "../services/api.js";

const initialForm = regionToForm(REGIONS[0]);

export default function PredictionForm({ onPrediction }) {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function selectRegion(event) {
    const region = REGIONS.find((item) => item.label === event.target.value);
    if (region) {
      setForm(regionToForm(region));
      setResult(null);
      setError("");
    }
  }

  function updateField(event) {
    const { name, value, type } = event.target;
    setForm((current) => ({ ...current, [name]: type === "number" ? Number(value) : value }));
  }

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const prediction = await predictDrought(form);
      setResult(prediction);
      await onPrediction();
    } catch (caught) {
      setError(caught.message || "Prediction failed. Is the backend running on localhost:8000?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <h2 className="text-lg font-bold">Prediction Form</h2>
      <label className="mt-4 block text-sm font-medium text-slate-600">
        Select region
        <select
          value={`${form.district}, ${form.state}`}
          onChange={selectRegion}
          className="mt-1 w-full rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3 font-semibold text-slate-900 outline-none focus:border-emerald-500"
        >
          {REGIONS.map((region) => (
            <option key={region.label} value={region.label}>
              {region.label}
            </option>
          ))}
        </select>
      </label>
      <form onSubmit={submit} className="mt-4 grid grid-cols-2 gap-3">
        {Object.entries(form).map(([key, value]) => (
          <label key={key} className="text-sm font-medium text-slate-600">
            {key.replaceAll("_", " ")}
            <input
              name={key}
              type={typeof value === "number" ? "number" : "text"}
              step="0.01"
              value={value}
              onChange={updateField}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-slate-900 outline-none focus:border-emerald-500"
            />
          </label>
        ))}
        <button disabled={loading} className="col-span-2 rounded-xl bg-emerald-600 px-4 py-3 font-bold text-white hover:bg-emerald-700">
          {loading ? "Predicting..." : "Predict Drought Severity"}
        </button>
      </form>
      {error && (
        <div className="mt-4 rounded-2xl bg-red-50 p-4 text-sm font-semibold text-red-700">
          {error}
        </div>
      )}
      {result && (
        <div className="mt-4 rounded-2xl bg-emerald-50 p-4">
          <p className="text-sm font-semibold text-emerald-700">Result</p>
          <p className="text-2xl font-black">{result.severity}</p>
          <p>Probability: {(result.probability * 100).toFixed(1)}% · Risk score: {result.risk_score}</p>
          <p className="mt-2 text-sm text-slate-700">{result.recommendation}</p>
          {result.suitable_crops?.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-bold text-slate-800">Suitable crops/plants</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {result.suitable_crops.map((crop) => (
                  <span key={crop} className="rounded-full bg-white px-3 py-1 text-xs font-bold text-emerald-700 ring-1 ring-emerald-200">
                    {crop}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function regionToForm(region) {
  const { label, ...form } = region;
  return form;
}
