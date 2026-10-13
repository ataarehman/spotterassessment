# Weather-Aware Truck Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React + Django app that plans three real alternative truck routes, samples weather at each checkpoint's arrival time, classifies risk with the PDF rules, and recommends a route by the PDF ranking order.

**Architecture:** Django REST Framework owns geocoding, routing, weather, risk, and ranking. The browser sends origin, destination, departure, load weight, and checkpoint spacing, then renders the returned GeoJSON on a single MapLibre map. The 0–48 hour heatmap updates an existing GeoJSON source. Pure Python modules hold the rules so pytest can cover every boundary without HTTP.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS, MapLibre GL JS, react-map-gl, Django 4.2, Django REST Framework, Open-Meteo hourly forecast, GraphHopper for route-planner UX and three alternatives (`GRAPHHOPPER_API_KEY` on the server), pytest-django, Playwright. Harbor is out of scope unless a separate coding-agent evaluation is requested.

## Global Constraints

- PDF is the source of truth: origin, destination, departure date/time, load weight; exactly three route options from a routing API; checkpoints every 10, 25, or 50 miles; weather at estimated arrival time; risk table plus the three load rules; rank by fewest Severe miles, then fewest High miles, then lowest average risk, then shortest travel time.
- Show routes, checkpoints, risk levels, ETAs, and summaries on a map, plus a corridor heatmap with a 0–48 hour slider.
- Do not invent weather values. Do not synthesize route geometry when the routing API returns fewer than three routes.
- External API keys stay on the server. Open-Meteo needs none.
- Prioritize correctness and clarity. A partial backend scaffold already exists under `backend/` and must be aligned with this plan, not grown around it.
- Python 3.9 is the available interpreter, so Django stays on 4.2.x and type hints stay 3.9-compatible.

---

## Assumptions (PDF is silent)

1. **Combined hazard.** Wind, rain, and snow are classified separately. Checkpoint risk is the worst of the three after the load adjustment is applied to wind only.
2. **Band edges.** Wind bands do not overlap: `<25`, `25–34` inclusive, `35–44` inclusive, `45–54` inclusive, `≥55`. Rain and snow rows share endpoints (`0.25`, `0.50`, `1.0`, `2.0`, `3.0`). A shared endpoint uses the higher severity. `>1.00` in/hr rain and `>3.0` in/hr snow are No Travel; `1.00` rain and `3.0` snow stay Severe.
3. **Load adjustment.** `≥55 mph` is No Travel for every load. `45–54 mph` and weight `> 30000` lb becomes No Travel. `35–44 mph` and weight `> 40000` lb becomes Severe. Weight equal to 30000 or 40000 does not trigger the "greater than" rules. Load rules never lower a rain or snow class.
4. **Risky miles.** Each segment between consecutive checkpoints, including origin and destination, is counted in miles toward the worse risk of its two endpoints. That is the exposure while traveling the segment.
5. **Average risk.** Distance-weighted mean of ordinal scores: Low 1, Moderate 2, High 3, Severe 4, No Travel 5. Ranking compares this number ascending.
6. **No Travel in ranking.** The PDF order does not name No Travel miles. Any route with No Travel miles sorts after every route with none. Among those, fewer No Travel miles wins, then the PDF order. The recommended route is still returned, with `has_no_travel: true` when that is the case.
7. **Missing weather.** A null wind, rain, or snow value at a checkpoint marks that checkpoint `Unknown`. A route with any Unknown checkpoint is not recommended. The API returns `recommendation: null` and an explicit error code `missing_weather` if every route is incomplete. Partial nulls are never filled with guesses.
8. **Arrival time.** `eta = departure + duration * (distance_along / route_distance)` using the routing API's duration. Weather is the hourly value whose interval contains that ETA. Forecast hours are not interpolated. The weather request must start at or before departure and include every hour through the latest checkpoint ETA on the longest route, even when that arrival is more than 48 hours after departure. The slider stays 0–48 hours from departure. If the provider cannot cover an ETA, that checkpoint is `Unknown` and the route is not recommended.
9. **Spacing.** The client chooses 10, 25, or 50 miles. Checkpoints include the start, every multiple of the spacing along the polyline, and the destination even when the last gap is shorter.
10. **Routes.** Prefer a real truck profile. If `HERE_API_KEY` is set, call HERE Routing v8 with `transportMode=truck` and request three alternatives. If `TOMTOM_API_KEY` is set and HERE is not, call TomTom truck routing and require three alternatives. Public OSRM driving is only the fallback when neither key is set, and the API response must include `routing_provider` and `truck_restrictions: false` in that case. Fewer than three distinct geometries is an error `insufficient_routes`. Never invent offset coordinates.
11. **Units.** Request Open-Meteo `wind_speed_unit=mph` and `precipitation_unit=inch`. `precipitation` is the hourly total and is treated as in/hr. `snowfall` is centimeters per hour and is converted with `/ 2.54` to in/hr. Document this conversion in the README.
12. **Heatmap versus checkpoints.** Checkpoint risk uses arrival time. The slider shows corridor conditions at `departure + N hours` for N in 0..48. Each heatmap point carries real hourly `wind_mph`, `rain_in_hr`, and `snow_in_hr` for those 49 hours. The UI can switch the painted hazard. The slider does not reclassify the trip recommendation.
13. **Tie break.** Equal ranking keys keep the routing API's original order.

## File structure

- `backend/planner/risk.py` — band classification, load adjustment, worst-of.
- `backend/planner/checkpoints.py` — polyline distance, spacing, ETAs.
- `backend/planner/ranking.py` — mile totals and lexicographic order.
- `backend/planner/routing.py` — OSRM or HERE, three routes only.
- `backend/planner/weather.py` — Open-Meteo hourly fetch and hour lookup.
- `backend/planner/services.py` — compose a trip plan.
- `backend/planner/views.py` — `POST /api/plan`.
- `backend/planner/tests/test_risk.py`, `test_checkpoints.py`, `test_ranking.py`, `test_plan_api.py`.
- `frontend/src/components/MapView.tsx` — one map, `setData` for routes and heatmap.
- `frontend/src/components/TripForm.tsx`, `RouteList.tsx`, `App.tsx`.
- `frontend/e2e/plan.spec.ts` — Playwright against mocked plan JSON.
- `docker-compose.yml`, `README.md`, `docs/WALKTHROUGH.md`.

## Requirement-to-test matrix

| PDF requirement | Test |
| --- | --- |
| Wind `<25`, `25–34`, `35–44`, `45–54`, `≥55` | `test_wind_band_edges` |
| Rain edges including shared `0.25`, `0.50`, `1.00`, and `>1` | `test_rain_band_edges` |
| Snow edges including shared `0.5`, `1.0`, `2.0`, `3.0`, and `>3` | `test_snow_band_edges` |
| `≥55 mph` No Travel for any load | `test_wind_55_any_load` |
| `45–54` and `>30000` lb No Travel; `30000` stays Severe | `test_load_45_boundary` |
| `35–44` and `>40000` lb Severe; `40000` stays High | `test_load_35_boundary` |
| Worst of wind, rain, snow | `test_worst_hazard_wins` |
| Load rule does not reduce rain/snow | `test_load_does_not_lower_precip` |
| Checkpoints at 10/25/50 including ends | `test_checkpoint_spacing` |
| ETA proportional to distance and API duration | `test_eta_uses_duration_fraction` |
| Forecast hour is the hour containing ETA | `test_sample_hour_containing_eta` |
| Null forecast stays Unknown | `test_missing_sample_is_unknown` |
| Severe miles, then High, then average, then duration | `test_rank_pdf_order` |
| No Travel routes sort after clean routes | `test_no_travel_sorts_last` |
| Three router geometries required | `test_fewer_than_three_routes_errors` |
| Plan response has checkpoints, risks, recommendation | `test_plan_api_with_fakes` |
| Slider updates heatmap source without a new map | Playwright `heatmap slider updates source data` |
| Form validation and three route cards | Playwright `plans a trip from fixture` |

---

### Task 1: Risk bands and load adjustment

**Files:**
- Create: `backend/planner/risk.py`
- Test: `backend/planner/tests/test_risk.py`

**Interfaces:**
- Consumes: nothing
- Produces: `classify_wind(mph: float) -> str`, `classify_rain(inches_per_hour: float) -> str`, `classify_snow(inches_per_hour: float) -> str`, `apply_load(wind_class: str, wind_mph: float, weight_lb: float) -> str`, `combine(wind_class: str, rain_class: str, snow_class: str) -> str`, `RISK_SCORE: dict`

- [ ] **Step 1: Write the failing tests** listed in the matrix rows for wind, rain, snow, and load.
- [ ] **Step 2: Run** `pytest backend/planner/tests/test_risk.py -v` and confirm collection errors or failures.
- [ ] **Step 3: Implement** only those functions.
- [ ] **Step 4: Re-run the same pytest command and require pass.**
- [ ] **Step 5: Commit** `feat: classify weather risk and load adjustments`

### Task 2: Checkpoints and arrival times

**Files:**
- Create: `backend/planner/checkpoints.py`
- Test: `backend/planner/tests/test_checkpoints.py`

**Interfaces:**
- Consumes: route GeoJSON LineString coordinates as `[lng, lat]`
- Produces: `checkpoints(coords, spacing_miles, departure, duration_seconds) -> list[dict]` with `distance_miles`, `eta` (timezone-aware), `lng`, `lat`

- [ ] Write tests for a straight polyline longer than 50 miles at all three spacings, plus a short final gap.
- [ ] Confirm failure, implement haversine accumulation, re-run pytest, commit `feat: sample checkpoints at arrival time`.

### Task 3: Ranking

**Files:**
- Create: `backend/planner/ranking.py`
- Test: `backend/planner/tests/test_ranking.py`

**Interfaces:**
- Consumes: checkpoint risks and segment miles
- Produces: `summarize(checkpoints) -> {severe_miles, high_miles, no_travel_miles, average_risk, unknown}` and `rank(routes) -> list` sorted by the assumption-6 key, then PDF order, then input order

- [ ] Tests construct three in-memory routes so order is Severe miles first, then High miles, then average risk, then duration, with a No Travel route last.
- [ ] Implement, pass pytest, commit `feat: rank routes by the assessment order`.

### Task 4: Weather hour lookup

**Files:**
- Create: `backend/planner/weather.py`
- Test: `backend/planner/tests/test_weather.py`

**Interfaces:**
- Produces: `sample_at(hourly: dict, eta) -> {wind_mph, rain_in_hr, snow_in_hr} | None` and `fetch_hourly(points, start)` which calls Open-Meteo and converts snowfall cm to inches. Tests pass a recorded hourly payload. The HTTP function is tested with `responses` or a stub, not live weather in unit tests.

- [ ] Assert the hour containing 14:20 is the 14:00 slot, a null wind yields None, and snowfall `2.54` cm becomes `1.0` in.
- [ ] Implement, pass, commit `feat: read hourly forecast at checkpoint ETA`.

### Task 5: Routing client

**Files:**
- Create: `backend/planner/routing.py`
- Test: `backend/planner/tests/test_routing.py`

**Interfaces:**
- Produces: `fetch_routes(origin, destination) -> list[Route]` of length 3, each with `geometry`, `distance_meters`, `duration_seconds`. Raises `InsufficientRoutes` below 3.

- [ ] Stub an OSRM payload with two routes and expect the error. Stub three routes and expect their coordinates unchanged.
- [ ] Implement OSRM parsing, and the HERE branch only when `HERE_API_KEY` is set. Commit `feat: require three routing-api alternatives`.

### Task 6: Plan service and API

**Files:**
- Modify: `backend/planner/services.py`, `backend/planner/views.py`, `backend/config/urls.py`
- Test: `backend/planner/tests/test_plan_api.py`

**Interfaces:**
- `POST /api/plan` body: `origin`, `destination` (strings), `departure` (ISO-8601), `weight_lb` (number), `spacing_miles` (10, 25, or 50).
- Response: `routes[]` with geometry, checkpoints (risk, weather, eta), summaries, `recommended_route_id`, `heatmap` points with 49 hours of wind mph.

- [ ] API test uses fakes for geocode, routes, and weather. Assert load-adjusted checkpoint classes and the recommended id.
- [ ] Assert 400 for bad spacing and 502-style JSON `{error: "insufficient_routes"}` when the router stub returns two routes.
- [ ] Commit `feat: expose trip planning API`.

### Task 7: Dashboard UI

**Files:**
- Create: `frontend/` Vite React TypeScript Tailwind app
- Components listed above

**Interfaces:**
- Consumes `POST /api/plan`. Map created once in an effect with empty deps. Slider calls `source.setData`. Route emphasis is a paint property update.

- [ ] Playwright uses `page.route` to fulfill `/api/plan` with a fixture of three real-shaped LineStrings, then checks three route names, checkpoint text, keyboard access to the form, and that slider movement does not change the map instance count.
- [ ] Visual direction: night dispatch desk. Fraunces for the title, Source Sans 3 for UI, ink background, amber for Severe, signal red for No Travel. No purple gradient, no Inter.
- [ ] Commit `feat: add trip map dashboard`.

### Task 8: Errors, cache, production deployment, docs

**Files:**
- `backend/planner/cache.py` using Django locmem keyed by rounded coordinates and hour
- `backend/Dockerfile` running gunicorn
- `frontend/Dockerfile` building the Vite app and serving it with nginx, proxying `/api` to the backend
- `docker-compose.yml` for local production-shaped run (`web` + `api`), not a dev-only preview
- `README.md` with units, band edges, load rules, No Travel ranking assumption, snowfall conversion, truck-routing key order (HERE, then TomTom, then OSRM fallback), and deploy steps
- `docs/WALKTHROUGH.md` with a 5–10 minute Loom outline: form, three routes, one checkpoint ETA versus forecast hour, load rule example, ranking sort, slider and hazard switch

- [ ] Pytest still passes. Playwright still passes against the fixture.
- [ ] Commit `docs: record rules, run steps, and walkthrough outline`.

## Spec coverage check

- Inputs: Task 6 and Task 7.
- Three routes: Task 5.
- Spacing and arrival weather: Tasks 2, 4, 6.
- Risk table and load rules: Task 1.
- Recommendation order: Task 3.
- Map, checkpoints, summaries, heatmap: Task 7.
- Hosted app and walkthrough: Task 8. GitHub publish and Loom recording stay with the user.

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-10-13-weather-aware-truck-routing.md`. Next work is Task 1 only: failing risk tests, then the risk module.
