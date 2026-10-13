# Final Spotter audit

Checked on 2026-10-13 against `/Users/app/Downloads/fs-assessment-spotter.pdf` and commit `2fc534e` plus the local Docker app at `http://127.0.0.1:8080`. Public hosting was not completed in this pass.

## VPS and DNS

| Check | Result |
| --- | --- |
| SSH | Root login to `209.126.9.159` succeeded. Host `vmi3251693`, 18 CPUs, 94 GiB RAM (78 GiB available), 118 GiB disk free |
| `mernify.co` A | `209.126.9.159` |
| `spotter.mernify.co` A | No answer. Authority is the GoDaddy SOA. The name does not resolve |
| Random label `any-random-label.mernify.co` | No A record. A `*.mernify.co` wildcard is not published |
| Existing certificate `/etc/letsencrypt/live/mernify.co` | DNS names are only `mernify.co` and `www.mernify.co`. It does not cover `spotter.mernify.co` |
| Nginx | 1.24.0, listening on 80 and 443, many unrelated vhosts. No `spotter` vhost |
| Free loopback port | `127.0.0.1:8092` had no listener |
| Other containers | Left running. Nothing was stopped or restarted |

Shared Nginx, certificates, firewall, and DNS were not changed.

## Requirement traceability

| PDF requirement | Implementation | Evidence | Status | Outstanding |
| --- | --- | --- | --- | --- |
| Origin and destination | `frontend/src/App.tsx`, `planner/services.py` geocode | Live Playwright and browser trip | PASS | |
| Departure date and time | Form `datetime-local`, ETA math in `planner/checkpoints.py` | pytest `test_eta_uses_duration_fraction`; live ETAs | PASS | |
| Load weight | Form field `weight_lb` | pytest load boundaries | PASS | |
| Three genuine alternative routes | `planner/clients.py` GraphHopper `alternative_route` | Live plan returned 3 distinct `car` geometries. `truck` HTTP 400 | PARTIAL | Account cannot request `truck` |
| Checkpoints at 10, 25, or 50 miles | `planner/checkpoints.py` | pytest spacing; live UI used 25 and 50 | PASS | |
| Weather at checkpoint arrival | `sample_at` on the hour containing the ETA | Live checkpoints had wind, rain, and snow | PASS | |
| Wind, rain, and snow thresholds | `planner/risk.py` | pytest band edges, 31 passed | PASS | |
| Load adjustments | `apply_load` | pytest `test_load_45_boundary`, `test_load_35_boundary`, `test_wind_55_any_load` | PASS | |
| Rank: Severe, High, average risk, time | `planner/ranking.py` | pytest `test_rank_pdf_order`. Live route with High miles sorted last | PASS | No Travel sorting after clean routes is a documented assumption |
| Map, checkpoints, risks, ETAs, summaries | `frontend/src/MapView.tsx`, route cards | Live browser and `e2e/live.spec.ts` 1 passed | PASS | |
| 0–48 hour heatmap, wind/rain/snow | Heatmap source plus slider | API returned 49 hours and 0 nulls. Slider moved to hour 6 in Playwright and hour 12 in the earlier browser session | PARTIAL | Hour 48 was not separately exercised in the browser |
| GitHub repository | Local branch `feature/weather-aware-truck-routing`, commits `79e0ff6`, `42e7599`, `2fc534e` | `git status` clean aside from this audit. No remote push | PARTIAL | Push needs approval. No GitHub URL confirmed |
| Hosted application | Not deployed | DNS and certificate do not cover the hostname | BLOCKED | DNS A record, Nginx vhost, and a certificate for `spotter.mernify.co` |
| 5–10 minute Loom | `docs/WALKTHROUGH.md` script only | No video file | BLOCKED | Recording has not been made |

## Tests last recorded

- pytest with `RUN_LIVE_PLAN=1`: 31 passed in 20.99 seconds.
- Mocked Playwright `e2e/plan.spec.ts`: 2 passed in 6.9 seconds.
- Live Playwright `e2e/live.spec.ts` against `http://127.0.0.1:8080`: 1 passed in 39.5 seconds. Browser wait 34.4 seconds. API total 33.8 seconds. Console error list empty.
- Cold 50-mile plan: 32.4 seconds wall, weather 28.9 seconds. Immediate repeat: 3.3 seconds, `weather_ms` 0.

These figures are from the local Docker stack, not from `https://spotter.mernify.co`.
