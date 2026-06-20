import React, { useEffect, useMemo, useState } from "react";
import Dashboard from "./pages/Dashboard.jsx";
import Analytics from "./pages/Analytics.jsx";
import SindhPso from "./pages/SindhPso.jsx";
import ResearchResults from "./pages/ResearchResults.jsx";
import {
  AdminPage,
  AuthPage,
  CropRecommendationPage,
  ExplainabilityPage,
  FarmerAdvisoryPage,
  ForecastDashboard,
  HistoricalAnalysis,
  InteractiveMapPage,
  LandingPage
} from "./pages/ProductionSuite.jsx";
import BenchmarkPanel from "./components/BenchmarkPanel.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import { fetchHistory, logoutSession } from "./services/api.js";

const pages = {
  "/": "dashboard",
  "/auth": "auth",
  "/login": "auth",
  "/signup": "auth",
  "/classic-dashboard": "classic-dashboard",
  "/analytics": "analytics",
  "/benchmark": "benchmark",
  "/sindh-pso": "sindh-pso",
  "/research-results": "research-results",
  "/forecast-dashboard": "forecast-dashboard",
  "/interactive-map": "interactive-map",
  "/historical-analysis": "historical-analysis",
  "/explainability": "explainability",
  "/crop-recommendation": "crop-recommendation",
  "/farmer-advisory": "farmer-advisory",
  "/admin": "admin",
  "/unauthorized": "unauthorized"
};

const publicPages = new Set(["dashboard", "auth"]);
const adminPages = new Set(["admin"]);
const farmerPages = new Set([
  "forecast-dashboard",
  "interactive-map",
  "historical-analysis",
  "explainability",
  "crop-recommendation",
  "farmer-advisory",
  "research-results",
  "sindh-pso",
  "classic-dashboard",
  "analytics",
  "benchmark"
]);

const labels = {
  dashboard: "Home",
  "forecast-dashboard": "Forecast",
  "interactive-map": "Map",
  "historical-analysis": "History",
  explainability: "Explainability",
  "crop-recommendation": "Crops",
  "farmer-advisory": "Advisory",
  "research-results": "Research Results",
  "sindh-pso": "Sindh PSO Model",
  admin: "Admin"
};

function pageFromPath() {
  return pages[window.location.pathname] || "dashboard";
}

export default function App() {
  const [page, setPage] = useState(pageFromPath());
  const [history, setHistory] = useState([]);
  const auth = useAuth();

  async function refreshHistory() {
    if (!auth.isAuthenticated) return;
    setHistory(await fetchHistory());
  }

  useEffect(() => {
    const syncPage = () => setPage(pageFromPath());
    window.addEventListener("popstate", syncPage);
    return () => window.removeEventListener("popstate", syncPage);
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [auth.isAuthenticated]);

  function navigate(nextPage) {
    const path = Object.entries(pages).find(([, value]) => value === nextPage)?.[0] || "/";
    window.history.pushState({}, "", path);
    setPage(nextPage);
  }

  function handleAuth(session) {
    auth.persistSession(session);
    navigate(session.user?.role === "ADMIN" ? "admin" : "forecast-dashboard");
  }

  async function handleLogout() {
    try {
      if (auth.accessToken && auth.refreshToken) {
        await logoutSession(auth.accessToken, auth.refreshToken);
      }
    } finally {
      auth.clearSession();
      navigate("auth");
    }
  }

  const visibleNav = useMemo(() => {
    if (!auth.isAuthenticated) return ["dashboard", "auth"];
    const base = ["dashboard", ...farmerPages];
    return auth.isAdmin ? [...base, "admin"] : base;
  }, [auth.isAuthenticated, auth.isAdmin]);

  const blockedPage = resolveBlockedPage(page, auth);
  const effectivePage = blockedPage || page;

  useEffect(() => {
    if (!auth.loading && blockedPage === "auth") navigate("auth");
    if (!auth.loading && blockedPage === "unauthorized") navigate("unauthorized");
  }, [auth.loading, blockedPage]);

  return (
    <main className="min-h-screen">
      <nav className="border-b border-emerald-100 bg-[#fbf8ef]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
          <button className="brand-button" onClick={() => navigate("dashboard")}>
            <p className="text-sm font-semibold text-emerald-700">AgriShield-X</p>
            <h1 className="text-xl font-bold text-stone-950">Agricultural Drought Early Warning</h1>
          </button>
          <div className="flex flex-wrap items-center gap-2">
            {visibleNav.map((item) => (
              <button
                key={item}
                onClick={() => navigate(item)}
                className={`rounded-full px-4 py-2 text-sm font-semibold ${
                  effectivePage === item ? "bg-emerald-700 text-white" : "bg-white/70 text-stone-700 shadow-sm"
                }`}
              >
                {labels[item] || "Login"}
              </button>
            ))}
            {auth.isAuthenticated && (
              <button onClick={handleLogout} className="rounded-full bg-stone-900 px-4 py-2 text-sm font-semibold text-white">
                Logout
              </button>
            )}
          </div>
        </div>
      </nav>
      {auth.loading ? <LoadingScreen /> : renderPage(effectivePage, { history, refreshHistory, handleAuth, auth })}
    </main>
  );
}

function resolveBlockedPage(page, auth) {
  if (auth.loading || publicPages.has(page)) return null;
  if (!auth.isAuthenticated) return "auth";
  if (adminPages.has(page) && !auth.isAdmin) return "unauthorized";
  if (farmerPages.has(page) || adminPages.has(page)) return null;
  return null;
}

function renderPage(page, props) {
  if (page === "dashboard") return <LandingPage />;
  if (page === "auth") return <AuthPage onAuth={props.handleAuth} />;
  if (page === "unauthorized") return <UnauthorizedPage user={props.auth.user} />;
  if (page === "classic-dashboard") return <Dashboard history={props.history} onPrediction={props.refreshHistory} />;
  if (page === "forecast-dashboard") return <ForecastDashboard />;
  if (page === "interactive-map") return <InteractiveMapPage />;
  if (page === "historical-analysis") return <HistoricalAnalysis />;
  if (page === "explainability") return <ExplainabilityPage />;
  if (page === "crop-recommendation") return <CropRecommendationPage />;
  if (page === "farmer-advisory") return <FarmerAdvisoryPage />;
  if (page === "admin") return <AdminPage />;
  if (page === "analytics") return <Analytics history={props.history} />;
  if (page === "sindh-pso") return <SindhPso />;
  if (page === "research-results") return <ResearchResults />;
  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <BenchmarkPanel />
    </div>
  );
}

function LoadingScreen() {
  return (
    <div className="agri-page">
      <section className="clay-panel">
        <p className="agri-kicker">Checking session</p>
        <h2>Preparing AgriShield-X</h2>
      </section>
    </div>
  );
}

function UnauthorizedPage({ user }) {
  return (
    <div className="agri-page">
      <section className="clay-panel">
        <p className="agri-kicker">Access denied</p>
        <h2>Admin authorization required</h2>
        <p>{user?.email || "This account"} can use farmer forecasting pages, but cannot open the admin console.</p>
      </section>
    </div>
  );
}
