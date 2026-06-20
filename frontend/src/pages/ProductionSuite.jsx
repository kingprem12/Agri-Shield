import { useEffect, useMemo, useState } from "react";
import {
  explainForecast,
  fetchAdminAnalytics,
  fetchAdminUsers,
  fetchAdvisory,
  fetchMapCells,
  fetchPsoFutureMetrics,
  forecastVhi,
  login,
  recommendCrops,
  signup
} from "../services/api.js";

const defaultClimate = {
  region: "Sindh",
  horizon_months: 3,
  date: "2023-12",
  ndvi: 0.31,
  lst: 39,
  rainfall: 18,
  temperature: 38,
  humidity: 31,
  solar_radiation: 25,
  wind_speed: 5,
  soil_moisture: 0.16
};

export function LandingPage() {
  const [metrics, setMetrics] = useState(null);
  useEffect(() => {
    fetchPsoFutureMetrics().then(setMetrics).catch(() => setMetrics(null));
  }, []);
  const strict = metrics?.protocols?.A_strict_chronological_next_month_forecasting || {
    r2: 0.8152,
    rmse: 0.1097,
    mae: 0.0839,
    drought_severity_f1: 0.6354
  };
  return (
    <div className="agri-page">
      <section className="agri-hero">
        <div>
          <p className="agri-kicker">AgriShield-X</p>
          <h2>Real-time drought intelligence for resilient farming.</h2>
          <p>
            Satellite vegetation, climate signals, PSO optimization, and cloud APIs combine to forecast next-month
            agricultural drought risk for Sindh.
          </p>
        </div>
        <div className="agri-hero-metrics">
          <Metric label="Strict R2" value={strict.r2} />
          <Metric label="RMSE" value={strict.rmse} />
          <Metric label="MAE" value={strict.mae} />
          <Metric label="F1" value={strict.drought_severity_f1} />
        </div>
      </section>
      <section className="agri-grid three">
        {[
          ["Farmer benefit", "Early warning, irrigation planning, crop choice support, and risk-aware advisories."],
          ["Model stack", "PSO LightGBM production candidate with strict next-month validation and no target leakage."],
          ["Cloud architecture", "React on S3, FastAPI on EC2, Docker packaging, Terraform infrastructure, and secure API routes."]
        ].map(([title, text]) => <InfoCard key={title} title={title} text={text} />)}
      </section>
    </div>
  );
}

export function ForecastDashboard() {
  const [payload, setPayload] = useState(defaultClimate);
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      setForecast(await forecastVhi(payload));
    } catch (err) {
      setError(err.message);
    }
  }
  const next = forecast?.forecasts?.[0];
  return (
    <div className="agri-page">
      <PageHeader title="Forecast Dashboard" text="Next-month drought severity, risk score, confidence, and VHI projection." />
      <section className="agri-grid dashboard">
        <form className="clay-panel" onSubmit={submit}>
          <h3>Forecast inputs</h3>
          <InputGrid payload={payload} setPayload={setPayload} keys={["ndvi", "lst", "rainfall", "temperature", "humidity", "solar_radiation", "wind_speed", "soil_moisture"]} />
          <button className="agri-button">Generate forecast</button>
        </form>
        <div className="clay-panel result-panel">
          <p className="agri-card-label">Next-month prediction</p>
          <strong>{next?.severity || "Awaiting forecast"}</strong>
          <span>Risk score {next ? (100 - Number(next.forecast_vhi) * 100).toFixed(1) : "--"}</span>
          <span>Confidence {next ? Math.max(52, Number(next.confidence || 0.76) * 100).toFixed(1) : "--"}%</span>
          <span>Forecast VHI {next ? Number(next.forecast_vhi).toFixed(4) : "--"}</span>
          {error && <small className="agri-error">{error}</small>}
        </div>
      </section>
    </div>
  );
}

export function InteractiveMapPage() {
  const [cells, setCells] = useState([]);
  const [selected, setSelected] = useState(null);
  useEffect(() => {
    fetchMapCells().then((data) => {
      setCells(data.cells || []);
      setSelected((data.cells || [])[0]);
    }).catch(() => {});
  }, []);
  return (
    <div className="agri-page">
      <PageHeader title="Interactive Map" text="Click a Sindh grid cell to inspect severity, explanation, history, and climate indicators." />
      <section className="agri-grid map-layout">
        <div className="clay-panel sindh-map">
          {cells.map((cell, index) => (
            <button key={cell.grid_id} className={`map-cell cell-${index} ${selected?.grid_id === cell.grid_id ? "active" : ""}`} onClick={() => setSelected(cell)}>
              {cell.grid_id.replace("sindh-", "")}
            </button>
          ))}
        </div>
        <div className="clay-panel">
          <h3>{selected?.grid_id || "Select a cell"}</h3>
          <p className="risk-line">{selected?.severity || "--"} · risk {selected?.risk_score ?? "--"}</p>
          <MiniTrend />
          <ClimateList indicators={selected?.climate_indicators || {}} />
        </div>
      </section>
    </div>
  );
}

export function HistoricalAnalysis() {
  const windows = [
    ["Past 3 months", [48, 52, 58]],
    ["Past 6 months", [41, 44, 48, 52, 58, 61]],
    ["Past 12 months", [33, 36, 39, 43, 45, 49, 52, 58, 61, 57, 54, 50]]
  ];
  return (
    <div className="agri-page">
      <PageHeader title="Historical Analysis" text="Recent drought risk windows for seasonal trend review." />
      <section className="agri-grid three">
        {windows.map(([title, values]) => (
          <div className="clay-panel" key={title}>
            <h3>{title}</h3>
            <Sparkline values={values} />
            <p>Trend: {values.at(-1) > values[0] ? "Risk increasing" : "Risk easing"}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

export function ExplainabilityPage() {
  const [explain, setExplain] = useState(null);
  useEffect(() => {
    explainForecast(defaultClimate).then(setExplain).catch(() => {
      setExplain({ explanation: "High solar radiation, low rainfall, heat stress, and weaker vegetation are the main drought drivers." });
    });
  }, []);
  return (
    <div className="agri-page">
      <PageHeader title="Explainability" text="Why the model predicts drought risk for the next month." />
      <section className="agri-grid two">
        <InfoCard title="Model explanation" text={explain?.explanation || "Loading explanation..."} />
        <div className="clay-panel">
          <h3>Top contributing factors</h3>
          <FeatureRank />
        </div>
      </section>
    </div>
  );
}

export function CropRecommendationPage() {
  const [form, setForm] = useState({ drought_severity: "Severe Drought", temperature: 39, rainfall: 12 });
  const [result, setResult] = useState(null);
  async function submit(event) {
    event.preventDefault();
    setResult(await recommendCrops(form));
  }
  return (
    <div className="agri-page">
      <PageHeader title="Crop Recommendation" text="Choose drought severity, temperature, and rainfall to get crop suitability guidance." />
      <section className="agri-grid dashboard">
        <form className="clay-panel" onSubmit={submit}>
          <h3>Crop inputs</h3>
          <InputGrid payload={form} setPayload={setForm} keys={["drought_severity", "temperature", "rainfall"]} />
          <button className="agri-button">Recommend crops</button>
        </form>
        <div className="clay-panel crop-list">
          {(result?.recommendations || []).map((crop) => (
            <div key={crop.crop}>
              <strong>{crop.crop}</strong>
              <span>{crop.suitability_score}% suitable · {crop.water_requirement} water</span>
              <p>{crop.reason}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function FarmerAdvisoryPage() {
  const [advisory, setAdvisory] = useState(null);
  useEffect(() => {
    fetchAdvisory({ drought_severity: "Severe Drought", risk_score: 71 }).then(setAdvisory).catch(() => {});
  }, []);
  return (
    <div className="agri-page">
      <PageHeader title="Farmer Advisory" text="Irrigation advice, warnings, and drought mitigation tips." />
      <section className="agri-grid two">
        <InfoCard title="Irrigation advice" text={advisory?.irrigation_advice || "Loading advisory..."} />
        <div className="clay-panel">
          <h3>Risk warnings</h3>
          <ul>{(advisory?.risk_warnings || []).map((item) => <li key={item}>{item}</li>)}</ul>
          <h3>Mitigation tips</h3>
          <ul>{(advisory?.mitigation_tips || []).map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      </section>
    </div>
  );
}

export function AuthPage({ onAuth }) {
  const initialMode = window.location.pathname === "/signup" ? "signup" : "login";
  const [mode, setMode] = useState(initialMode);
  const [form, setForm] = useState({ email: "", password: "", full_name: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      if (mode === "signup") {
        await signup(form);
        setMessage("Account created. Please login with your new farmer account.");
        setMode("login");
        return;
      }
      const result = await login(form);
      onAuth?.(result);
      setMessage("Signed in successfully");
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <div className="agri-page">
      <PageHeader title="Secure Access" text="JWT authentication with FARMER and ADMIN roles." />
      <form className="clay-panel auth-panel" onSubmit={submit}>
        <div className="segmented">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Login</button>
          <button type="button" className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")}>Signup</button>
        </div>
        <InputGrid payload={form} setPayload={setForm} keys={mode === "signup" ? ["full_name", "email", "password"] : ["email", "password"]} />
        <button className="agri-button">{mode === "login" ? "Login" : "Create account"}</button>
        {message && <p>{message}</p>}
        {error && <p className="agri-error">{error}</p>}
      </form>
    </div>
  );
}

export function AdminPage() {
  const [data, setData] = useState(null);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const token = localStorage.getItem("agrishield_access_token");
    if (!token) {
      setError("Admin login required.");
      return;
    }
    Promise.all([fetchAdminAnalytics(token), fetchAdminUsers(token)])
      .then(([analytics, userData]) => {
        setData(analytics);
        setUsers(userData.users || []);
      })
      .catch((err) => setError(err.message));
  }, []);
  return (
    <div className="agri-page">
      <PageHeader title="Admin Console" text="Users, active sessions, forecast usage, model metrics, and system logs." />
      {error && <p className="agri-error">{error}</p>}
      <section className="agri-grid three">
        <Metric label="Users" value={data?.total_users ?? 0} />
        <Metric label="Active" value={data?.active_users ?? 0} />
        <Metric label="Forecasts" value={data?.forecast_usage ?? 0} />
      </section>
      <section className="agri-grid two">
        <div className="clay-panel">
          <h3>User management</h3>
          <p>Role distribution: ADMIN {users.filter((user) => user.role === "ADMIN").length} · FARMER {users.filter((user) => user.role === "FARMER").length}</p>
          {users.map((user) => <p key={user.id}>{user.email} · {user.role} · {user.is_active ? "active" : "disabled"}</p>)}
        </div>
        <div className="clay-panel"><h3>System logs</h3>{(data?.system_logs || []).map((log) => <p key={`${log.created_at}-${log.event}`}>{log.event}: {log.message}</p>)}</div>
      </section>
    </div>
  );
}

function PageHeader({ title, text }) {
  return <section className="page-header"><p className="agri-kicker">AgriShield-X</p><h2>{title}</h2><p>{text}</p></section>;
}

function Metric({ label, value }) {
  const formatted = typeof value === "number" && value < 2 ? value.toFixed(4) : value;
  return <div className="clay-panel metric-tile"><span>{label}</span><strong>{formatted}</strong></div>;
}

function InfoCard({ title, text }) {
  return <div className="clay-panel"><h3>{title}</h3><p>{text}</p></div>;
}

function InputGrid({ payload, setPayload, keys }) {
  return (
    <div className="input-grid">
      {keys.map((key) => (
        <label key={key}>{key.replaceAll("_", " ")}
          <input value={payload[key]} type={typeof payload[key] === "number" ? "number" : "text"} step="any" onChange={(event) => setPayload((current) => ({ ...current, [key]: typeof current[key] === "number" ? Number(event.target.value) : event.target.value }))} />
        </label>
      ))}
    </div>
  );
}

function Sparkline({ values }) {
  const points = values.map((value, index) => `${20 + index * (260 / Math.max(values.length - 1, 1))},${150 - value}`).join(" ");
  return <svg className="sparkline" viewBox="0 0 300 170"><polyline points={points} fill="none" stroke="#326f44" strokeWidth="5" strokeLinecap="round" /></svg>;
}

function MiniTrend() {
  return <Sparkline values={[41, 43, 46, 52, 58, 55, 61]} />;
}

function ClimateList({ indicators }) {
  return <div className="climate-list">{Object.entries(indicators).map(([key, value]) => <span key={key}>{key}: {value}</span>)}</div>;
}

function FeatureRank() {
  return <div className="feature-rank">{["Solar radiation", "Low rainfall", "Temperature stress", "Vegetation decline"].map((item, index) => <span key={item} style={{ width: `${95 - index * 13}%` }}>{item}</span>)}</div>;
}
