import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "../src/App.jsx";
import { AuthProvider } from "../src/context/AuthContext.jsx";
import { fetchProfile, login } from "../src/services/api.js";

vi.mock("../src/services/api.js", () => ({
  explainForecast: vi.fn().mockResolvedValue({ explanation: "Low rainfall increased drought risk." }),
  fetchAdminAnalytics: vi.fn().mockResolvedValue({ total_users: 2, active_users: 2, forecast_usage: 4, system_logs: [] }),
  fetchAdminUsers: vi.fn().mockResolvedValue({ users: [{ id: 1, email: "admin@test.local", role: "ADMIN", is_active: true }] }),
  fetchAdvisory: vi.fn().mockResolvedValue({ irrigation_advice: "Irrigate carefully.", risk_warnings: [], mitigation_tips: [] }),
  fetchHistory: vi.fn().mockResolvedValue([]),
  fetchMapCells: vi.fn().mockResolvedValue({ cells: [] }),
  fetchPsoFutureMetrics: vi.fn().mockResolvedValue({ protocols: {} }),
  fetchProfile: vi.fn(async (token) => ({
    id: 1,
    email: `${token}@test.local`,
    role: token === "admin-token" ? "ADMIN" : "FARMER",
    is_active: true
  })),
  forecastVhi: vi.fn(),
  login: vi.fn().mockResolvedValue({ access_token: "farmer-token", refresh_token: "refresh-token", user: { role: "FARMER", email: "farmer@test.local" } }),
  logoutSession: vi.fn().mockResolvedValue({ status: "ok" }),
  recommendCrops: vi.fn(),
  refreshSession: vi.fn()
}));

vi.mock("../src/pages/Dashboard.jsx", () => ({
  default: () => <div>Classic dashboard</div>
}));

vi.mock("../src/pages/Analytics.jsx", () => ({
  default: () => <div>Analytics dashboard</div>
}));

vi.mock("../src/pages/SindhPso.jsx", () => ({
  default: () => <div>Sindh PSO Model</div>
}));

vi.mock("../src/pages/ResearchResults.jsx", () => ({
  default: () => <div>Research Results</div>
}));

vi.mock("../src/components/BenchmarkPanel.jsx", () => ({
  default: () => <div>Benchmark panel</div>
}));

function renderApp(path) {
  window.history.pushState({}, "", path);
  return render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
});

test("unauthenticated users are redirected from protected pages to auth", async () => {
  renderApp("/forecast-dashboard");
  await screen.findByText("Secure Access");
  expect(window.location.pathname).toBe("/auth");
  expect(window.location.search).toBe("?redirect=%2Fforecast-dashboard");
});

test("public admin click redirects to auth with admin redirect", async () => {
  renderApp("/");
  await screen.findByText("Real-time drought intelligence for resilient farming.");
  fireEvent.click(screen.getByText("Admin"));
  await screen.findByText("Secure Access");
  expect(window.location.pathname).toBe("/auth");
  expect(window.location.search).toBe("?redirect=%2Fadmin");
});

test("farmer users cannot access admin", async () => {
  localStorage.setItem("agrishield_access_token", "farmer-token");
  renderApp("/admin");
  await screen.findByText("Admin authorization required");
});

test("admin users can view admin console", async () => {
  localStorage.setItem("agrishield_access_token", "admin-token");
  renderApp("/admin");
  await screen.findByText("Admin Console");
  await screen.findByText("User management");
});

test("admin login from admin redirect opens admin console", async () => {
  login.mockResolvedValueOnce({
    access_token: "admin-token",
    refresh_token: "refresh-token",
    role: "ADMIN",
    user: { role: "ADMIN", email: "admin@test.local" }
  });
  renderApp("/admin");
  await screen.findByText("Secure Access");
  fireEvent.click(screen.getAllByText("Login").at(-1));
  await screen.findByText("Admin Console");
  expect(window.location.pathname).toBe("/admin");
});

test("farmer login from forecast redirect opens forecast dashboard", async () => {
  login.mockResolvedValueOnce({
    access_token: "farmer-token",
    refresh_token: "refresh-token",
    role: "USER",
    user: { role: "USER", email: "farmer@test.local" }
  });
  renderApp("/forecast-dashboard");
  await screen.findByText("Secure Access");
  fireEvent.click(screen.getAllByText("Login").at(-1));
  await screen.findByText("Forecast Dashboard");
  expect(window.location.pathname).toBe("/forecast-dashboard");
});

test("invalid saved token clears session and redirects to auth", async () => {
  fetchProfile.mockRejectedValueOnce(new Error("Profile failed: 401"));
  localStorage.setItem("agrishield_access_token", "bad-token");
  renderApp("/forecast-dashboard");
  await screen.findByText("Secure Access");
  expect(localStorage.getItem("agrishield_access_token")).toBeNull();
  expect(window.location.pathname).toBe("/auth");
});

test("logout clears the session and returns to auth", async () => {
  localStorage.setItem("agrishield_access_token", "farmer-token");
  localStorage.setItem("agrishield_refresh_token", "refresh-token");
  renderApp("/forecast-dashboard");
  await screen.findByText("Forecast Dashboard");
  fireEvent.click(screen.getByText("Logout"));
  await waitFor(() => expect(localStorage.getItem("agrishield_access_token")).toBeNull());
  await screen.findByText("Secure Access");
});
