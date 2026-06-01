const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
  const response = await fetch(`${API_BASE_URL}/history`);
  if (!response.ok) return [];
  return response.json();
}

export async function forecastVhi(payload) {
  const response = await fetch(`${API_BASE_URL}/forecast`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
