import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "../src/App.jsx";
import { AuthProvider } from "../src/context/AuthContext.jsx";
import { fetchProfile, login } from "../src/services/api.js";

vi.mock("../src/services/api.js", () => ({
  explainForecast: vi.fn().mockResolvedValue({ explanation: "Low rainfall increased drought risk." }),
  fetchAdminAnalytics: vi.fn().mockResolvedValue({ total_users: 2, active_users: 2, forecast_usage: 4, system_logs: [] }),
  fetchAdminDatasets: vi.fn().mockResolvedValue({ rows: 1361299, grid_cells: 4937, date_range: "2001-2023" }),
  fetchAdminLogs: vi.fn().mockResolvedValue({ logs: [] }),
  fetchAdminModels: vi.fn().mockResolvedValue({ model: "PSO-Optimized LightGBM", r2: 0.8153, rmse: 0.1097, mae: 0.0839, f1: 0.6354 }),
  fetchAdminUsers: vi.fn().mockResolvedValue({ users: [{ id: 1, email: "admin@test.local", role: "ADMIN", is_active: true }] }),
  fetchAdvisory: vi.fn().mockResolvedValue({ irrigation_advice: "Irrigate carefully.", risk_warnings: [], mitigation_tips: [] }),
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
  refreshSession: vi.fn(),
  signup: vi.fn().mockResolvedValue({ user: { role: "FARMER" } })
}));

vi.mock("../src/pages/SindhPso.jsx", () => ({
  default: () => <div>Sindh PSO Model</div>
}));

vi.mock("../src/pages/ResearchResults.jsx", () => ({
  default: () => <div>Research Results</div>
}));

function renderApp(path) {
  window.history.pushState({}, "", path);
  return render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

function fillLogin(email = "demo@test.local", password = "Password@123") {
  const inputs = document.querySelectorAll("input");
  fireEvent.change(inputs[0], { target: { value: email } });
  fireEvent.change(inputs[1], { target: { value: password } });
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

test("logged out admin redirects to admin login with redirect query", async () => {
  renderApp("/admin");
  await screen.findByRole("heading", { name: "Admin Login" });
  expect(window.location.pathname).toBe("/auth/admin");
  expect(window.location.search).toBe("?redirect=%2Fadmin");
});

test("logged out farmer dashboard redirects to farmer login with redirect query", async () => {
  renderApp("/dashboard");
  await screen.findByRole("heading", { name: "Farmer Login" });
  expect(window.location.pathname).toBe("/auth/farmer");
  expect(window.location.search).toBe("?redirect=%2Fdashboard");
});

test("public navbar has one farmer login and one admin login with no logout", async () => {
  renderApp("/");
  await screen.findByText("Role-based drought intelligence for farmers and administrators.");
  expect(screen.getAllByText("Farmer Login")).toHaveLength(1);
  expect(screen.getAllByText("Admin Login")).toHaveLength(1);
  expect(screen.queryByText("Logout")).not.toBeInTheDocument();
});

test("admin login opens admin dashboard and admin navbar only", async () => {
  login.mockResolvedValueOnce({
    access_token: "admin-token",
    refresh_token: "refresh-token",
    role: "ADMIN",
    user: { role: "ADMIN", email: "admin@test.local" }
  });
  renderApp("/admin");
  await screen.findByRole("heading", { name: "Admin Login" });
  fillLogin("admin@test.local", "Password@123");
  fireEvent.click(screen.getByText("Login as admin"));
  await screen.findByRole("heading", { name: "Admin Dashboard" });
  expect(fetchProfile).toHaveBeenCalledWith("admin-token");
  expect(window.location.pathname).toBe("/admin");
  expect(screen.getByText("Users")).toBeInTheDocument();
  expect(screen.queryByText("Farmer Login")).not.toBeInTheDocument();
});

test("farmer login opens farmer dashboard and farmer navbar only", async () => {
  login.mockResolvedValueOnce({
    access_token: "farmer-token",
    refresh_token: "refresh-token",
    role: "FARMER",
    user: { role: "FARMER", email: "farmer@test.local" }
  });
  renderApp("/dashboard");
  await screen.findByRole("heading", { name: "Farmer Login" });
  fillLogin("farmer@test.local", "Password@123");
  fireEvent.click(screen.getByText("Login as farmer"));
  await screen.findByText("Farmer Dashboard");
  expect(fetchProfile).toHaveBeenCalledWith("farmer-token");
  expect(window.location.pathname).toBe("/dashboard");
  expect(screen.getByText("Forecast")).toBeInTheDocument();
  expect(screen.queryByText("Admin Dashboard")).not.toBeInTheDocument();
});

test("farmer cannot access admin", async () => {
  localStorage.setItem("agrishield_access_token", "farmer-token");
  renderApp("/admin");
  await screen.findByText("Access denied");
  expect(window.location.pathname).toBe("/unauthorized");
});

test("invalid saved token clears session and redirects to role login", async () => {
  fetchProfile.mockRejectedValueOnce(new Error("Profile failed: 401"));
  localStorage.setItem("agrishield_access_token", "bad-token");
  renderApp("/dashboard");
  await screen.findByRole("heading", { name: "Farmer Login" });
  expect(localStorage.getItem("agrishield_access_token")).toBeNull();
  await waitFor(() => expect(window.location.pathname).toBe("/auth/farmer"));
});

test("logout clears session and returns to farmer login", async () => {
  localStorage.setItem("agrishield_access_token", "farmer-token");
  localStorage.setItem("agrishield_refresh_token", "refresh-token");
  renderApp("/dashboard");
  await screen.findByText("Farmer Dashboard");
  fireEvent.click(screen.getByText("Logout"));
  await waitFor(() => expect(localStorage.getItem("agrishield_access_token")).toBeNull());
  await screen.findByRole("heading", { name: "Farmer Login" });
  expect(window.location.pathname).toBe("/auth/farmer");
});
