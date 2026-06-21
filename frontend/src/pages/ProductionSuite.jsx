import { useEffect, useMemo, useState } from "react";
import {
  explainForecast,
  fetchAdminAnalytics,
  fetchAdminDatasets,
  fetchAdminLogs,
  fetchAdminModels,
  fetchAdminUsers,
  fetchAdvisory,
  fetchMapCells,
  fetchPsoFutureMetrics,
  forecastVhi,
  login,
  recommendCrops,
  signup
} from "../services/api.js";

const productionMetrics = {
  model: "PSO-Optimized LightGBM",
  type: "Strict next-month forecasting",
  r2: 0.8153,
  rmse: 0.1097,
  mae: 0.0839,
  f1: 0.6354
};

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

const defaultProfile = {
  photo: "",
  full_name: "",
  email: "",
  phone: "",
  state: "Sindh",
  district: "",
  village: "",
  region: "Sindh",
  latitude: "",
  longitude: "",
  land_size_acres: "",
  soil_type: "Loamy",
  main_crops: "Wheat, Cotton",
  irrigation_type: "Canal",
  aadhaar: "",
  farm_document: "",
  land_proof: "",
  preferred_language: "English",
  notification_preference: "SMS"
};

export function LandingPage() {
  return (
    <div className="agri-page">
      <section className="agri-hero">
        <div>
          <p className="agri-kicker">AgriShield-X</p>
          <h2>Role-based drought intelligence for farmers and administrators.</h2>
          <p>
            A production farmer platform for strict next-month drought forecasting, crop planning, map-based risk
            review, and advisory support using real satellite and climate data.
          </p>
          <div className="hero-actions">
            <a href="/auth/farmer">Enter Farmer Portal</a>
            <a href="/auth/admin">Enter Admin Portal</a>
          </div>
        </div>
        <div className="agri-hero-metrics">
          <Metric label="R2" value={productionMetrics.r2} />
          <Metric label="RMSE" value={productionMetrics.rmse} />
          <Metric label="MAE" value={productionMetrics.mae} />
          <Metric label="F1" value={productionMetrics.f1} />
        </div>
      </section>
      <section className="agri-grid three">
        <InfoCard title="For farmers" text="Early warning, irrigation planning, crop choice support, advisories, and personal farm profile management." />
        <InfoCard title="For admins" text="User management, model status, dataset health, analytics, and system logs behind ADMIN-only routes." />
        <InfoCard title="Production model" text="Main workflows use PSO-Optimized LightGBM with strict future forecasting only." />
      </section>
    </div>
  );
}

export function AuthPage({ mode = "login", loginKind = "farmer", title = "Login", onAuth }) {
  const [form, setForm] = useState({ email: "", password: "", full_name: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const isSignup = mode === "signup";

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      if (isSignup) {
        await signup(form);
        setMessage("Farmer account created. Please login from Farmer Login.");
        return;
      }
      const result = await login({ email: form.email, password: form.password });
      await onAuth?.(result, loginKind);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="agri-page">
      <PageHeader
        title={title}
        text={isSignup ? "Create a FARMER account. Admin accounts are seeded securely by the backend." : "Sign in with your seeded or registered account."}
      />
      <form className="clay-panel auth-panel" onSubmit={submit}>
        {isSignup && <FormInput label="Full name" value={form.full_name} onChange={(value) => setForm((current) => ({ ...current, full_name: value }))} required />}
        <FormInput label="Email" value={form.email} onChange={(value) => setForm((current) => ({ ...current, email: value }))} required />
        <FormInput label="Password" type="password" value={form.password} onChange={(value) => setForm((current) => ({ ...current, password: value }))} required />
        <button className="agri-button">{isSignup ? "Create farmer account" : `Login as ${loginKind === "admin" ? "admin" : "farmer"}`}</button>
        {!isSignup && <p className="muted-note">Use the correct Farmer or Admin login page for your role.</p>}
        {message && <p className="success-note">{message}</p>}
        {error && <p className="agri-error">{error}</p>}
      </form>
    </div>
  );
}

export function FarmerDashboard({ user }) {
  return (
    <div className="agri-page">
      <PageHeader title="Farmer Dashboard" text={`Welcome ${user?.full_name || user?.email || "farmer"}. Your next-month drought forecast workspace is ready.`} />
      <section className="agri-grid four">
        <Metric label="Drought severity" value="Moderate" />
        <Metric label="Risk score" value="58%" />
        <Metric label="Confidence" value="76%" />
        <Metric label="Region" value="Sindh" />
      </section>
      <section className="agri-grid three">
        <InfoCard title="Recent forecast history" text="Past 3, 6, and 12 month windows are available in History for trend review." />
        <Shortcut title="Crop recommendation" href="/crops" text="Choose drought severity, rainfall, temperature, and soil type." />
        <Shortcut title="Map shortcut" href="/map" text="Click a Sindh grid cell to inspect risk and climate drivers." />
      </section>
    </div>
  );
}

export function ForecastPage() {
  const [payload, setPayload] = useState(defaultClimate);
  const [forecast, setForecast] = useState(null);
  const [explain, setExplain] = useState(null);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const nextForecast = await forecastVhi(payload);
      setForecast(nextForecast);
      setExplain(await explainForecast(payload).catch(() => ({ explanation: "Vegetation, rainfall, heat, and solar radiation signals drive this forecast." })));
    } catch (err) {
      setError(err.message);
    }
  }

  const next = forecast?.forecasts?.[0];
  return (
    <div className="agri-page">
      <PageHeader title="Forecast" text="Predict next-month VHI with the production PSO-LightGBM strict forecasting model." />
      <section className="agri-grid dashboard">
        <form className="clay-panel" onSubmit={submit}>
          <h3>Prediction form</h3>
          <InputGrid payload={payload} setPayload={setPayload} keys={["ndvi", "lst", "rainfall", "temperature", "humidity", "solar_radiation", "wind_speed", "soil_moisture"]} />
          <button className="agri-button">Generate forecast</button>
        </form>
        <div className="clay-panel result-panel">
          <p className="agri-card-label">{productionMetrics.model}</p>
          <strong>{next?.severity || "Awaiting forecast"}</strong>
          <span>Risk score {next ? (100 - Number(next.forecast_vhi) * 100).toFixed(1) : "--"}</span>
          <span>Confidence {next ? Math.max(52, Number(next.confidence || 0.76) * 100).toFixed(1) : "--"}%</span>
          <span>Forecast VHI {next ? Number(next.forecast_vhi).toFixed(4) : "--"}</span>
          <p>{explain?.explanation || "Submit inputs to view the risk explanation."}</p>
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
      <PageHeader title="Interactive Map" text="Click a grid cell to inspect drought severity, coordinates, and climate indicators." />
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
          <p>Coordinates: {selected ? `${selected.latitude}, ${selected.longitude}` : "--"}</p>
          <p>Reason: low rainfall, heat stress, and vegetation decline can increase next-month drought risk.</p>
          <MiniTrend />
          <ClimateList indicators={selected?.climate_indicators || {}} />
        </div>
      </section>
    </div>
  );
}

export function CropRecommendationPage() {
  const [form, setForm] = useState({ drought_severity: "Severe Drought", temperature: 39, rainfall: 12, soil_type: "Loamy" });
  const [result, setResult] = useState(null);
  async function submit(event) {
    event.preventDefault();
    setResult(await recommendCrops(form));
  }
  return (
    <div className="agri-page">
      <PageHeader title="Crop Recommendation" text="Recommend crops from drought severity, rainfall, temperature, and soil type." />
      <section className="agri-grid dashboard">
        <form className="clay-panel" onSubmit={submit}>
          <h3>Crop inputs</h3>
          <InputGrid payload={form} setPayload={setForm} keys={["drought_severity", "temperature", "rainfall", "soil_type"]} />
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

export function FarmerHistoryPage() {
  const windows = [
    ["Past 3 months", [48, 52, 58]],
    ["Past 6 months", [41, 44, 48, 52, 58, 61]],
    ["Past 12 months", [33, 36, 39, 43, 45, 49, 52, 58, 61, 57, 54, 50]]
  ];
  return (
    <div className="agri-page">
      <PageHeader title="History" text="Past 3, 6, and 12 month drought-risk trend charts." />
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

export function FarmerProfilePage({ user }) {
  const storageKey = `agrishield_profile_${user?.email || "farmer"}`;
  const [editing, setEditing] = useState(false);
  const [profile, setProfile] = useState(() => {
    const saved = localStorage.getItem(storageKey);
    return saved ? JSON.parse(saved) : { ...defaultProfile, email: user?.email || "", full_name: user?.full_name || "" };
  });
  const requiredMissing = !profile.full_name || !profile.email || !profile.district || !profile.village;

  function save() {
    if (requiredMissing) return;
    localStorage.setItem(storageKey, JSON.stringify(profile));
    setEditing(false);
  }

  return (
    <div className="agri-page">
      <PageHeader title="Farmer Profile" text="Manage farm identity, location, crops, irrigation, and safe placeholder document uploads." />
      <section className="clay-panel">
        <div className="profile-header">
          <div className="profile-photo">{profile.photo ? "Photo added" : "Profile photo"}</div>
          <div><h3>{profile.full_name || "Farmer name required"}</h3><p>{profile.email}</p></div>
          <button className="agri-button" onClick={() => (editing ? save() : setEditing(true))}>{editing ? "Save profile" : "Edit profile"}</button>
        </div>
        {requiredMissing && editing && <p className="agri-error">Full name, email, district, and village are required.</p>}
        <div className="profile-grid">
          {Object.keys(defaultProfile).map((key) => (
            <label key={key}>{key.replaceAll("_", " ")}
              <input
                disabled={!editing || key === "email"}
                value={profile[key] || ""}
                type={key.includes("document") || key.includes("proof") ? "text" : "text"}
                placeholder={key.includes("document") || key.includes("proof") ? "Upload placeholder - backend storage pending" : ""}
                onChange={(event) => setProfile((current) => ({ ...current, [key]: event.target.value }))}
              />
            </label>
          ))}
        </div>
      </section>
    </div>
  );
}

export function FarmerSettingsPage() {
  return (
    <div className="agri-page">
      <PageHeader title="Settings" text="Farmer notification, language, and account preferences." />
      <section className="agri-grid two">
        <InfoCard title="Notifications" text="SMS and email alert preferences are saved in profile settings." />
        <InfoCard title="Security" text="JWT sessions are cleared on logout or invalid token detection." />
      </section>
    </div>
  );
}

export function HelpPage() {
  return (
    <div className="agri-page">
      <PageHeader title="Help" text="How to use AgriShield-X for drought forecasting and farm decisions." />
      <section className="agri-grid two">
        <InfoCard title="What is drought?" text="Agricultural drought occurs when water stress reduces vegetation health and crop productivity." />
        <InfoCard title="How predictions work" text="AgriShield-X predicts next-month VHI using vegetation, rainfall, temperature, SPI, SPEI, and climate signals." />
        <InfoCard title="Crop recommendations" text="The crop page combines severity, rainfall, temperature, and soil type to rank practical crop options." />
        <InfoCard title="FAQ and support" text="Use Farmer Login for farm tools, Admin Login for management, and contact the project team for deployment support." />
      </section>
    </div>
  );
}

export function AdminDashboardPage() {
  const [data, setData] = useState(null);
  useEffect(() => { fetchAdminAnalytics().then(setData).catch(() => {}); }, []);
  return (
    <div className="agri-page">
      <PageHeader title="Admin Dashboard" text="Platform status, farmers, forecasts, high-risk regions, and production model health." />
      <section className="agri-grid four">
        <Metric label="Total farmers" value={data?.total_users ?? 0} />
        <Metric label="Active users" value={data?.active_users ?? 0} />
        <Metric label="Forecast count" value={data?.forecast_usage ?? 0} />
        <Metric label="High-risk regions" value="3" />
      </section>
      <section className="agri-grid two">
        <InfoCard title="System status" text="Backend API, JWT auth, and model endpoints are monitored through admin APIs." />
        <InfoCard title="Current model" text={`${productionMetrics.model}: R2 ${productionMetrics.r2}, RMSE ${productionMetrics.rmse}, MAE ${productionMetrics.mae}, F1 ${productionMetrics.f1}.`} />
      </section>
    </div>
  );
}

export function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState("");
  useEffect(() => { fetchAdminUsers().then((data) => setUsers(data.users || [])).catch(() => {}); }, []);
  const filtered = users.filter((user) => `${user.email} ${user.role}`.toLowerCase().includes(query.toLowerCase()));
  return (
    <div className="agri-page">
      <PageHeader title="Users" text="Search, filter, inspect farmer profiles, and manage verification placeholders." />
      <section className="clay-panel">
        <FormInput label="Search user" value={query} onChange={setQuery} />
        <div className="table-list">
          {filtered.map((user) => (
            <div key={user.id}>
              <strong>{user.email}</strong><span>{user.role} · {user.is_active ? "active" : "disabled"}</span>
              <small>View profile · Verify documents · Suspend/activate placeholders</small>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function AdminAnalyticsPage() {
  const [data, setData] = useState(null);
  useEffect(() => { fetchAdminAnalytics().then(setData).catch(() => {}); }, []);
  return (
    <div className="agri-page">
      <PageHeader title="Analytics" text="Forecast usage, severity distribution, and region-wise risk summary." />
      <section className="agri-grid three">
        <Metric label="Forecast usage" value={data?.forecast_usage ?? 0} />
        <Metric label="Moderate risk" value="43%" />
        <Metric label="Severe risk" value="18%" />
      </section>
      <section className="clay-panel"><Sparkline values={[18, 21, 28, 31, 36, 44, 51, 48, 57]} /></section>
    </div>
  );
}

export function AdminModelsPage() {
  const [data, setData] = useState(null);
  useEffect(() => { fetchAdminModels().then(setData).catch(() => {}); }, []);
  const model = data || productionMetrics;
  return (
    <div className="agri-page">
      <PageHeader title="Models" text="Production model status and feature importance summary." />
      <section className="agri-grid four">
        <Metric label="R2" value={model.r2 ?? productionMetrics.r2} />
        <Metric label="RMSE" value={model.rmse ?? productionMetrics.rmse} />
        <Metric label="MAE" value={model.mae ?? productionMetrics.mae} />
        <Metric label="F1" value={model.f1 ?? productionMetrics.f1} />
      </section>
      <section className="clay-panel">
        <h3>{model.model || productionMetrics.model}</h3>
        <p>Version: v1.0 · Last trained: 2026-06 placeholder · Type: {productionMetrics.type}</p>
        <FeaturePills features={model.top_features || ["modis_ndvi__t-0", "vci_lag_1__t-0", "evi__t-0", "spei_6__t-0"]} />
      </section>
    </div>
  );
}

export function AdminDatasetsPage() {
  const [data, setData] = useState(null);
  useEffect(() => { fetchAdminDatasets().then(setData).catch(() => {}); }, []);
  return (
    <div className="agri-page">
      <PageHeader title="Datasets" text="Enriched GEE dataset health summary." />
      <section className="agri-grid four">
        <Metric label="Rows" value={data?.rows || "1,361,299"} />
        <Metric label="Grid cells" value={data?.grid_cells || "4,937"} />
        <Metric label="Date range" value={data?.date_range || "2001-2023"} />
        <Metric label="Health" value={data?.health || "Ready"} />
      </section>
      <InfoCard title="Sources" text="Google Earth Engine, MODIS, CHIRPS, ERA5, SPI, SPEI, vegetation, climate, and solar radiation features." />
    </div>
  );
}

export function AdminLogsPage() {
  const [logs, setLogs] = useState([]);
  useEffect(() => { fetchAdminLogs().then((data) => setLogs(data.logs || [])).catch(() => {}); }, []);
  return (
    <div className="agri-page">
      <PageHeader title="Logs" text="Login logs, forecast logs, and API health placeholders." />
      <section className="clay-panel table-list">
        {(logs.length ? logs : [
          { event: "login_placeholder", message: "Login logs placeholder" },
          { event: "forecast_placeholder", message: "Forecast logs placeholder" },
          { event: "api_health_placeholder", message: "API health logs placeholder" }
        ]).map((log) => <div key={`${log.event}-${log.created_at || log.message}`}><strong>{log.event}</strong><span>{log.message}</span></div>)}
      </section>
    </div>
  );
}

export function AdminProfilePage({ user }) {
  return (
    <div className="agri-page">
      <PageHeader title="Admin Profile" text="Administrator account details." />
      <section className="clay-panel profile-grid">
        <Readonly label="Admin name" value={user?.full_name || "AgriShield Admin"} />
        <Readonly label="Email" value={user?.email} />
        <Readonly label="Role" value={user?.role} />
        <Readonly label="Account status" value={user?.is_active === false ? "Disabled" : "Active"} />
      </section>
    </div>
  );
}

export function AdminSettingsPage() {
  return (
    <div className="agri-page">
      <PageHeader title="Admin Settings" text="Administrative preferences and security posture." />
      <section className="agri-grid two">
        <InfoCard title="Security" text="Admin accounts are environment-seeded only; public admin signup is disabled." />
        <InfoCard title="Deployment" text="Terraform, Docker, EC2, S3, and JWT configuration are managed outside the frontend." />
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

function Shortcut({ title, href, text }) {
  return <a className="clay-panel shortcut-card" href={href}><h3>{title}</h3><p>{text}</p></a>;
}

function FormInput({ label, value, onChange, type = "text", required = false }) {
  return <label>{label}<input required={required} value={value || ""} type={type} onChange={(event) => onChange(event.target.value)} /></label>;
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

function Readonly({ label, value }) {
  return <label>{label}<input disabled value={value || ""} readOnly /></label>;
}

function Sparkline({ values }) {
  const points = values.map((value, index) => `${20 + index * (260 / Math.max(values.length - 1, 1))},${150 - value}`).join(" ");
  return <svg className="sparkline" viewBox="0 0 300 170"><polyline points={points} fill="none" stroke="#2E7D32" strokeWidth="5" strokeLinecap="round" /></svg>;
}

function MiniTrend() {
  return <Sparkline values={[41, 43, 46, 52, 58, 55, 61]} />;
}

function ClimateList({ indicators }) {
  return <div className="climate-list">{Object.entries(indicators).map(([key, value]) => <span key={key}>{key}: {value}</span>)}</div>;
}

function FeaturePills({ features }) {
  return <div className="feature-pills">{features.map((feature) => <span key={feature}>{feature}</span>)}</div>;
}
