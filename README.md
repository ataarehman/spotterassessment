# Spotter weather-aware truck routing

Django plans three GraphHopper alternatives. Open-Meteo supplies the hourly forecast at each checkpoint's arrival time. React, MapLibre, and react-map-gl draw the routes, checkpoints, and a 0–48 hour corridor heatmap.

## Rules

Wind mph: `<25` Low, `25–34` Moderate, `35–44` High, `45–54` Severe, `≥55` No Travel. The 45–54 load rule uses `[45, 55)` and the 35–44 load rule uses `[35, 45)`.

Rain in/hr: `<0.10` Low, `0.10–0.25` Moderate, `0.25–0.50` High, `0.50–1.00` Severe, `>1.00` No Travel. Shared endpoints take the higher severity.

Snow in/hr: `<0.5` Low, `0.5–1.0` Moderate, `1.0–2.0` High, `2.0–3.0` Severe, `>3.0` No Travel. When Open-Meteo reports snowfall in inches, that value is used as in/hr. Centimeter values are divided by 2.54.

Load: `≥55` mph is No Travel for every load. `45–54` mph and weight above 30,000 lb is No Travel. `35–44` mph and weight above 40,000 lb is Severe. Checkpoint risk is the worst of adjusted wind, rain, and snow.

Segment miles use the worse endpoint. Routes with any No Travel miles sort after clean routes, then by fewest Severe miles, fewest High miles, lowest distance-weighted average risk (Low 1 through No Travel 5), then shortest duration. Missing weather leaves the checkpoint Unknown and removes the route from recommendation.

GraphHopper must return three distinct paths. This API key's account accepts only `car`, `bike`, and `foot`. `truck` returns HTTP 400, so the local default profile is `car` and the response includes `profile`. The server never invents geometry or fills missing forecast values. Open-Meteo HTTP 429 and 503 are retried up to four times with bounded exponential backoff and jitter (0.5s, 1s, 2s, capped at 8s). Locations are requested in batches of eight. A successful hourly series is cached in memory for 10 minutes and reused only when it still contains the departure hour. Expired or missing hours are fetched again. They are never replaced with guessed weather. The JSON field `timings_ms` reports geocode, routing, weather, risk, and total milliseconds.

## Run locally with Docker

From the repository root, with `.env` present and not committed:

```bash
docker compose config --quiet
docker compose up --build -d
```

The UI is at http://127.0.0.1:8080 and nginx proxies `/api` to the Django container. The published port is bound to 127.0.0.1 only.

Offline tests: `backend/.venv/bin/pytest backend/planner/tests -k 'not live'`. That command still runs `test_live_plan.py` only when `RUN_LIVE_PLAN=1`. Mocked browser tests: `cd frontend && npx playwright test`. Live browser smoke, against the local Docker UI only: `cd frontend && LIVE_BROWSER=1 npx playwright test e2e/live.spec.ts`.

## Troubleshooting

- `insufficient_routes`: GraphHopper returned fewer than three alternatives.
- `provider_unavailable`: missing key, unsupported profile, or Open-Meteo/GraphHopper HTTP error.
- `geocode_failed`: Open-Meteo geocoding found no match.
- Heatmap hours are null only when the provider omits that hour. A successful Dallas–Chicago check covered all 49 hours.
