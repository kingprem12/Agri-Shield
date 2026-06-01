import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles/index.css";
import Dashboard from "./pages/Dashboard.jsx";
import Analytics from "./pages/Analytics.jsx";
import BenchmarkPanel from "./components/BenchmarkPanel.jsx";
import { fetchHistory } from "./services/api.js";

function App() {
  const [page, setPage] = useState("dashboard");
  const [history, setHistory] = useState([]);

  async function refreshHistory() {
    setHistory(await fetchHistory());
  }

  useEffect(() => {
    refreshHistory();
  }, []);

  return (
    <main className="min-h-screen">
      <nav className="border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-sm font-semibold text-emerald-600">AgriShield AI</p>
            <h1 className="text-xl font-bold text-slate-950">Agricultural Drought Early Warning</h1>
          </div>
          <div className="flex gap-2">
            {["dashboard", "analytics", "benchmark"].map((item) => (
              <button
                key={item}
                onClick={() => setPage(item)}
                className={`rounded-full px-4 py-2 text-sm font-semibold ${
                  page === item ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-700"
                }`}
              >
                {item[0].toUpperCase() + item.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </nav>
      {page === "dashboard" ? (
        <Dashboard history={history} onPrediction={refreshHistory} />
      ) : page === "analytics" ? (
        <Analytics history={history} />
      ) : (
        <div className="mx-auto max-w-7xl px-6 py-8">
          <BenchmarkPanel />
        </div>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
