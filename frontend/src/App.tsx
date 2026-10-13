import { FormEvent, useState } from "react";
import { MapView } from "./MapView";
import type { Plan } from "./types";
import "./styles.css";

const empty = { origin: "Dallas", destination: "Chicago", weight: "35000", spacing: "25", departure: "2026-10-13T12:00" };

export function App() {
  const [form, setForm] = useState(empty);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [hour, setHour] = useState(0);
  const [hazard, setHazard] = useState<"wind_mph" | "rain_in_hr" | "snow_in_hr">("wind_mph");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          origin: form.origin,
          destination: form.destination,
          departure: new Date(form.departure).toISOString(),
          weight_lb: Number(form.weight),
          spacing_miles: Number(form.spacing),
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        setPlan(null);
        setError(body.message || "The planner could not build routes.");
        return;
      }
      setPlan(body);
      setSelected(body.recommended_route_id);
      setHour(0);
    } catch {
      setError("The planner is unreachable.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="desk">
      <header>
        <p className="kicker">Spotter dispatch</p>
        <h1>Weather-aware truck routing</h1>
      </header>
      <form onSubmit={onSubmit} aria-label="Trip plan">
        <label>Origin<input name="origin" value={form.origin} onChange={(e) => setForm({ ...form, origin: e.target.value })} required /></label>
        <label>Destination<input name="destination" value={form.destination} onChange={(e) => setForm({ ...form, destination: e.target.value })} required /></label>
        <label>Departure<input name="departure" type="datetime-local" value={form.departure} onChange={(e) => setForm({ ...form, departure: e.target.value })} required /></label>
        <label>Load weight (lb)<input name="weight" inputMode="decimal" value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} required /></label>
        <label>Checkpoint spacing
          <select name="spacing" value={form.spacing} onChange={(e) => setForm({ ...form, spacing: e.target.value })}>
            <option value="10">10 miles</option>
            <option value="25">25 miles</option>
            <option value="50">50 miles</option>
          </select>
        </label>
        <button type="submit" disabled={loading}>{loading ? "Planning…" : "Compare routes"}</button>
      </form>
      {error ? <p role="alert">{error}</p> : null}
      {plan ? (
        <section className="layout">
          <ol className="routes">
            {plan.routes.map((route) => (
              <li key={route.id}>
                <button type="button" aria-pressed={selected === route.id} onClick={() => setSelected(route.id)}>
                  <strong>{route.id}</strong>
                  {route.id === plan.recommended_route_id ? <span> Recommended</span> : null}
                  <span>{Math.round(route.duration_seconds / 60)} min</span>
                  <span>Severe {route.summary.severe_miles.toFixed(0)} mi</span>
                  <span>High {route.summary.high_miles.toFixed(0)} mi</span>
                  <span>No Travel {route.summary.no_travel_miles.toFixed(0)} mi</span>
                </button>
                <ul>
                  {route.checkpoints.map((stop) => (
                    <li key={stop.eta + stop.distance_miles}>
                      {stop.distance_miles.toFixed(0)} mi · {stop.risk ?? "Unknown"} · {new Date(stop.eta).toLocaleString()}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
          <div className="map-panel">
            <MapView plan={plan} selectedId={selected} hour={hour} hazard={hazard} />
            <label className="slider">Forecast hour {hour}
              <input aria-label="Forecast hour" type="range" min={0} max={48} value={hour} onChange={(e) => setHour(Number(e.target.value))} />
            </label>
            <div role="group" aria-label="Heatmap hazard">
              {(["wind_mph", "rain_in_hr", "snow_in_hr"] as const).map((item) => (
                <button key={item} type="button" aria-pressed={hazard === item} onClick={() => setHazard(item)}>
                  {item === "wind_mph" ? "Wind" : item === "rain_in_hr" ? "Rain" : "Snow"}
                </button>
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </main>
  );
}
