export type Hazard = "wind_mph" | "rain_in_hr" | "snow_in_hr";

export interface Checkpoint {
  distance_miles: number;
  eta: string;
  lng: number;
  lat: number;
  risk: string | null;
  weather: Record<Hazard, number> | null;
}

export interface RoutePlan {
  id: string;
  duration_seconds: number;
  geometry: { type: "LineString"; coordinates: number[][] };
  summary: { severe_miles: number; high_miles: number; no_travel_miles: number; average_risk: number | null; unknown: boolean };
  checkpoints: Checkpoint[];
}

export interface Plan {
  recommended_route_id: string | null;
  routes: RoutePlan[];
  heatmap: { lat: number; lng: number; hours: Array<Record<Hazard, number> | null> }[];
}
