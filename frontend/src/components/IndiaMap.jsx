import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

const defaultPoints = [
  { state: "Maharashtra", district: "Pune", latitude: 18.52, longitude: 73.85, risk_score: 46, severity: "Moderate Drought" },
  { state: "Rajasthan", district: "Jodhpur", latitude: 26.23, longitude: 73.02, risk_score: 68, severity: "Severe Drought" },
  { state: "Punjab", district: "Ludhiana", latitude: 30.9, longitude: 75.85, risk_score: 28, severity: "Mild Drought" }
];

function colorFor(score) {
  if (score >= 75) return "#7f1d1d";
  if (score >= 55) return "#ef4444";
  if (score >= 35) return "#f59e0b";
  return "#22c55e";
}

export default function IndiaMap({ history }) {
  const points = history.length ? history : defaultPoints;
  return (
    <MapContainer center={[22.5, 79]} zoom={5} scrollWheelZoom={false}>
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((point, index) => (
        <CircleMarker
          key={`${point.district}-${index}`}
          center={[point.latitude, point.longitude]}
          radius={10}
          pathOptions={{ color: colorFor(point.risk_score), fillColor: colorFor(point.risk_score), fillOpacity: 0.75 }}
        >
          <Popup>
            <strong>{point.district}, {point.state}</strong>
            <br />
            {point.severity} ({Number(point.risk_score).toFixed(1)})
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

