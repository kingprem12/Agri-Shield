import Plot from "react-plotly.js";

export default function RiskChart({ history }) {
  const recent = [...history].reverse().slice(-20);
  return (
    <Plot
      data={[
        {
          x: recent.map((item) => new Date(item.created_at).toLocaleDateString()),
          y: recent.map((item) => item.risk_score),
          type: "scatter",
          mode: "lines+markers",
          marker: { color: "#059669" }
        }
      ]}
      layout={{
        autosize: true,
        height: 330,
        margin: { l: 40, r: 20, t: 20, b: 40 },
        yaxis: { title: "Risk score", range: [0, 100] },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)"
      }}
      useResizeHandler
      className="w-full"
    />
  );
}

