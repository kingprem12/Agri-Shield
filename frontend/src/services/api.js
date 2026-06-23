const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const ACCESS_KEY = "agrishield_access_token";

function authHeaders(token = localStorage.getItem(ACCESS_KEY)) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function predictDrought(payload) {
  const response = await fetch(`${API_BASE_URL}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Prediction failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchHistory() {
  const response = await fetch(`${API_BASE_URL}/history`, { headers: authHeaders() });
  if (!response.ok) return [];
  return response.json();
}

export async function forecastVhi(payload) {
  const response = await fetch(`${API_BASE_URL}/forecast`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Forecast failed: ${response.status}`);
  }
  return response.json();
}

export async function explainForecast(payload) {
  const response = await fetch(`${API_BASE_URL}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Explain failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchResearchMetrics() {
  const response = await fetch(`${API_BASE_URL}/research-metrics`);
  if (!response.ok) {
    throw new Error(`Metrics failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchBenchmark() {
  const response = await fetch(`${API_BASE_URL}/benchmark`);
  if (!response.ok) {
    throw new Error(`Benchmark failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchPsoSindhMetrics() {
  const response = await fetch(`${API_BASE_URL}/pso-sindh/metrics`);
  if (!response.ok) {
    throw new Error(`PSO metrics failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchPsoSindhBenchmark() {
  const response = await fetch(`${API_BASE_URL}/pso-sindh/benchmark`);
  if (!response.ok) {
    throw new Error(`PSO benchmark failed: ${response.status}`);
  }
  return response.json();
}

export async function predictPsoSindh(payload) {
  const response = await fetch(`${API_BASE_URL}/pso-sindh/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`PSO prediction failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchPsoSindhFeatureImportance() {
  const response = await fetch(`${API_BASE_URL}/pso-sindh/feature-importance`);
  if (!response.ok) {
    throw new Error(`PSO feature importance failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchPsoFutureMetrics() {
  const response = await fetch(`${API_BASE_URL}/pso-future/metrics`);
  if (!response.ok) {
    throw new Error(`PSO future metrics failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchResearchResults() {
  const response = await fetch(`${API_BASE_URL}/research/results`);
  if (!response.ok) {
    throw new Error(`Research results failed: ${response.status}`);
  }
  return response.json();
}

export async function signup(payload) {
  const response = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: payload.email, password: payload.password, full_name: payload.full_name })
  });
  if (!response.ok) throw new Error(`Signup failed: ${response.status}`);
  return response.json();
}

export async function login(payload) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`Login failed: ${response.status}`);
  return response.json();
}

export async function logoutSession(token, refreshToken) {
  const response = await fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  if (!response.ok) throw new Error(`Logout failed: ${response.status}`);
  return response.json();
}

export async function refreshSession(refreshToken) {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  if (!response.ok) throw new Error(`Refresh failed: ${response.status}`);
  return response.json();
}

export async function fetchProfile(token) {
  const response = await fetch(`${API_BASE_URL}/auth/profile`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) throw new Error(`Profile failed: ${response.status}`);
  return response.json();
}

export async function fetchAdminAnalytics(token) {
  const response = await fetch(`${API_BASE_URL}/admin/analytics`, {
    headers: authHeaders(token)
  });
  if (!response.ok) throw new Error(`Admin analytics failed: ${response.status}`);
  return response.json();
}

export async function fetchAdminUsers(token) {
  const response = await fetch(`${API_BASE_URL}/admin/users`, {
    headers: authHeaders(token)
  });
  if (!response.ok) throw new Error(`Admin users failed: ${response.status}`);
  return response.json();
}

export async function fetchAdminProfile(token) {
  const response = await fetch(`${API_BASE_URL}/admin/profile`, {
    headers: authHeaders(token)
  });
  if (!response.ok) throw new Error(`Admin profile failed: ${response.status}`);
  return response.json();
}

export async function fetchAdminModels(token) {
  const response = await fetch(`${API_BASE_URL}/admin/models`, {
    headers: authHeaders(token)
  });
  if (!response.ok) throw new Error(`Admin models failed: ${response.status}`);
  return response.json();
}

export async function fetchAdminDatasets(token) {
  const response = await fetch(`${API_BASE_URL}/admin/datasets`, {
    headers: authHeaders(token)
  });
  if (!response.ok) throw new Error(`Admin datasets failed: ${response.status}`);
  return response.json();
}

export async function fetchAdminLogs(token) {
  const response = await fetch(`${API_BASE_URL}/admin/logs`, {
    headers: authHeaders(token)
  });
  if (!response.ok) throw new Error(`Admin logs failed: ${response.status}`);
  return response.json();
}

export async function fetchMapCells() {
  const response = await fetch(`${API_BASE_URL}/map`, { headers: authHeaders() });
  if (!response.ok) throw new Error(`Map failed: ${response.status}`);
  return response.json();
}

export async function recommendCrops(payload) {
  const response = await fetch(`${API_BASE_URL}/crops`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`Crop recommendation failed: ${response.status}`);
  return response.json();
}

export async function fetchAdvisory(payload) {
  const response = await fetch(`${API_BASE_URL}/advisories`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`Advisory failed: ${response.status}`);
  return response.json();
}
