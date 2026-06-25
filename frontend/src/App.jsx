import React, { useEffect, useMemo, useState } from "react";
import SindhPso from "./pages/SindhPso.jsx";
import ResearchResults from "./pages/ResearchResults.jsx";
import {
  AdminAnalyticsPage,
  AdminDashboardPage,
  AdminDatasetsPage,
  AdminLogsPage,
  AdminModelsPage,
  AdminProfilePage,
  AdminSettingsPage,
  AdminUsersPage,
  AuthPage,
  CropRecommendationPage,
  FarmerAdvisoryPage,
  FarmerDashboard,
  FarmerHistoryPage,
  FarmerProfilePage,
  FarmerSettingsPage,
  ForecastPage,
  HelpPage,
  InteractiveMapPage,
  LandingPage
} from "./pages/ProductionSuite.jsx";
import { normalizeRole, useAuth } from "./context/AuthContext.jsx";
import { logoutSession } from "./services/api.js";

const routeConfig = {
  "/": { page: "home", public: true },
  "/auth": { page: "farmer-login", public: true },
  "/auth/farmer": { page: "farmer-login", public: true },
  "/auth/admin": { page: "admin-login", public: true },
  "/login": { page: "farmer-login", public: true },
  "/signup": { page: "signup", public: true },
  "/help": { page: "help", public: true },

  "/dashboard": { page: "farmer-dashboard", roles: ["FARMER"] },
  "/forecast": { page: "forecast", roles: ["FARMER"] },
  "/map": { page: "map", roles: ["FARMER"] },
  "/crops": { page: "crops", roles: ["FARMER"] },
  "/advisories": { page: "advisories", roles: ["FARMER"] },
  "/history": { page: "history", roles: ["FARMER"] },
  "/profile": { page: "profile", roles: ["FARMER"] },
  "/settings": { page: "settings", roles: ["FARMER"] },
  "/research-results": { page: "research-results", roles: ["FARMER"] },
  "/sindh-pso": { page: "sindh-pso", roles: ["FARMER"] },

  "/admin": { page: "admin-dashboard", roles: ["ADMIN"] },
  "/admin/users": { page: "admin-users", roles: ["ADMIN"] },
  "/admin/analytics": { page: "admin-analytics", roles: ["ADMIN"] },
  "/admin/models": { page: "admin-models", roles: ["ADMIN"] },
  "/admin/datasets": { page: "admin-datasets", roles: ["ADMIN"] },
  "/admin/logs": { page: "admin-logs", roles: ["ADMIN"] },
  "/admin/profile": { page: "admin-profile", roles: ["ADMIN"] },
  "/admin/settings": { page: "admin-settings", roles: ["ADMIN"] },
  "/unauthorized": { page: "unauthorized", roles: ["FARMER", "ADMIN"] },

  "/forecast-dashboard": { redirect: "/dashboard" },
  "/interactive-map": { redirect: "/map" },
  "/historical-analysis": { redirect: "/history" },
  "/crop-recommendation": { redirect: "/crops" },
  "/farmer-advisory": { redirect: "/advisories" }
};

const publicNav = [
  ["/", "Home"],
  ["/auth/farmer", "Farmer Login"],
  ["/auth/admin", "Admin Login"],
  ["/help", "Help"]
];

const farmerNav = [
  ["/dashboard", "Dashboard"],
  ["/forecast", "Forecast"],
  ["/map", "Map"],
  ["/crops", "Crops"],
  ["/advisories", "Advisory"],
  ["/history", "History"],
  ["/research-results", "Research"],
  ["/sindh-pso", "Research Lab"],
  ["/help", "Help"],
  ["/profile", "Profile"]
];

const adminNav = [
  ["/admin", "Admin Dashboard"],
  ["/admin/users", "Users"],
  ["/admin/analytics", "Analytics"],
  ["/admin/models", "Models"],
  ["/admin/datasets", "Datasets"],
  ["/admin/logs", "Logs"],
  ["/admin/profile", "Profile"]
];

function currentPath() {
  return window.location.pathname || "/";
}

function redirectQuery() {
  const target = new URLSearchParams(window.location.search).get("redirect");
  return target && target.startsWith("/") ? target : "";
}

function loginPathFor(path) {
  return path.startsWith("/admin") ? "/auth/admin" : "/auth/farmer";
}

function configForPath(path) {
  return routeConfig[path] || routeConfig["/"];
}

function roleAllowed(config, role) {
  if (config.public) return true;
  const normalized = normalizeRole(role);
  if (normalized === "ADMIN") return config.roles?.includes("ADMIN");
  return config.roles?.includes("FARMER") && !config.roles?.includes("ADMIN");
}

export default function App() {
  const auth = useAuth();
  const [path, setPath] = useState(currentPath());

  useEffect(() => {
    const sync = () => setPath(currentPath());
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  const config = configForPath(path);

  useEffect(() => {
    if (config.redirect) {
      navigateTo(config.redirect, true);
    }
  }, [config.redirect]);

  useEffect(() => {
    if (auth.loading || config.public || config.redirect) return;
    if (!auth.isAuthenticated) {
      navigateTo(`${loginPathFor(path)}?redirect=${encodeURIComponent(path)}`, true);
      return;
    }
    if (!roleAllowed(config, auth.user?.role)) {
      navigateTo("/unauthorized", true);
    }
  }, [auth.loading, auth.isAuthenticated, auth.user?.role, path]);

  function navigateTo(nextPath, replace = false) {
    if (replace) {
      window.history.replaceState({}, "", nextPath);
    } else {
      window.history.pushState({}, "", nextPath);
    }
    setPath(currentPath());
  }

  async function handleAuth(session, loginKind = "farmer") {
    const profile = await auth.completeLogin(session);
    const role = normalizeRole(profile?.role);
    const requested = redirectQuery();
    if (requested) {
      const requestedConfig = configForPath(requested);
      if (!requestedConfig.public && roleAllowed(requestedConfig, role)) {
        navigateTo(requested, true);
        return;
      }
    }
    navigateTo(role === "ADMIN" ? "/admin" : "/dashboard", true);
  }

  async function handleLogout() {
    try {
      if (auth.accessToken && auth.refreshToken) {
        await logoutSession(auth.accessToken, auth.refreshToken);
      }
    } finally {
      auth.clearSession();
      navigateTo("/auth/farmer", true);
    }
  }

  const navItems = useMemo(() => {
    if (!auth.isAuthenticated) return publicNav;
    return auth.isAdmin ? adminNav : farmerNav;
  }, [auth.isAuthenticated, auth.isAdmin]);

  const effectiveConfig = configForPath(path);
  const effectivePage = effectiveConfig.page || "home";

  return (
    <main className="min-h-screen">
      <nav className="border-b border-emerald-100 bg-[#fbf8ef]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
          <button className="brand-button" onClick={() => navigateTo(auth.isAuthenticated ? (auth.isAdmin ? "/admin" : "/dashboard") : "/")}>
            <p className="text-sm font-semibold text-emerald-700">AgriShield-X</p>
            <h1 className="text-xl font-bold text-stone-950">Farmer Drought Intelligence Platform</h1>
          </button>
          <div className="flex flex-wrap items-center gap-2">
            {navItems.map(([href, label]) => (
              <button
                key={href}
                onClick={() => navigateTo(href)}
                className={`rounded-full px-4 py-2 text-sm font-semibold ${
                  path === href ? "bg-emerald-700 text-white" : "bg-white/70 text-stone-700 shadow-sm"
                }`}
              >
                {label}
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
      {auth.loading ? <LoadingScreen /> : renderPage(effectivePage, { auth, handleAuth })}
    </main>
  );
}

function renderPage(page, props) {
  if (page === "home") return <LandingPage />;
  if (page === "farmer-login") return <AuthPage mode="login" loginKind="farmer" title="Farmer Login" onAuth={props.handleAuth} />;
  if (page === "admin-login") return <AuthPage mode="login" loginKind="admin" title="Admin Login" onAuth={props.handleAuth} />;
  if (page === "signup") return <AuthPage mode="signup" loginKind="farmer" title="Farmer Signup" onAuth={props.handleAuth} />;
  if (page === "help") return <HelpPage />;
  if (page === "farmer-dashboard") return <FarmerDashboard user={props.auth.user} />;
  if (page === "forecast") return <ForecastPage />;
  if (page === "map") return <InteractiveMapPage />;
  if (page === "crops") return <CropRecommendationPage />;
  if (page === "advisories") return <FarmerAdvisoryPage />;
  if (page === "history") return <FarmerHistoryPage />;
  if (page === "profile") return <FarmerProfilePage user={props.auth.user} />;
  if (page === "settings") return <FarmerSettingsPage />;
  if (page === "research-results") return <ResearchResults />;
  if (page === "sindh-pso") return <SindhPso />;
  if (page === "admin-dashboard") return <AdminDashboardPage />;
  if (page === "admin-users") return <AdminUsersPage />;
  if (page === "admin-analytics") return <AdminAnalyticsPage />;
  if (page === "admin-models") return <AdminModelsPage />;
  if (page === "admin-datasets") return <AdminDatasetsPage />;
  if (page === "admin-logs") return <AdminLogsPage />;
  if (page === "admin-profile") return <AdminProfilePage user={props.auth.user} />;
  if (page === "admin-settings") return <AdminSettingsPage />;
  if (page === "unauthorized") return <UnauthorizedPage user={props.auth.user} />;
  return <LandingPage />;
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
        <p className="agri-kicker">403 Unauthorized</p>
        <h2>Access denied</h2>
        <p>{user?.email || "This account"} does not have permission to open that page.</p>
      </section>
    </div>
  );
}
