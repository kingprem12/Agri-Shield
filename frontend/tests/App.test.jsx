import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import Dashboard from "../src/pages/Dashboard.jsx";

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }) => <div data-testid="map">{children}</div>,
  TileLayer: () => <div />,
  CircleMarker: ({ children }) => <div>{children}</div>,
  Popup: ({ children }) => <div>{children}</div>
}));

vi.mock("react-plotly.js", () => ({
  default: () => <div data-testid="plot" />
}));

test("renders dashboard prediction form", () => {
  render(<Dashboard history={[]} onPrediction={vi.fn()} />);
  expect(screen.getByText("Interactive India Risk Map")).toBeInTheDocument();
  expect(screen.getByText("Prediction Form")).toBeInTheDocument();
});
