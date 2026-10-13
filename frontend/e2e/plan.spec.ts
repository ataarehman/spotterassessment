import { expect, test } from "@playwright/test";

const plan = {
  recommended_route_id: "route-1",
  routes: [1, 2, 3].map((index) => ({
    id: `route-${index}`,
    duration_seconds: 3600 * index,
    geometry: { type: "LineString", coordinates: [[-96.8, 32.7], [-90, 37 + index], [-87.6, 41.8]] },
    summary: { severe_miles: index, high_miles: index, no_travel_miles: 0, average_risk: 1, unknown: false },
    checkpoints: [
      { distance_miles: 0, eta: "2026-10-13T12:00:00+00:00", lng: -96.8, lat: 32.7, risk: "Low", weather: { wind_mph: 10, rain_in_hr: 0, snow_in_hr: 0 } },
      { distance_miles: 50, eta: "2026-10-13T13:00:00+00:00", lng: -90, lat: 37, risk: "High", weather: { wind_mph: 36, rain_in_hr: 0, snow_in_hr: 0 } },
    ],
  })),
  heatmap: [
    { lat: 37, lng: -90, hours: Array.from({ length: 49 }, (_, hour) => ({ wind_mph: hour, rain_in_hr: hour / 100, snow_in_hr: 0 })) },
  ],
};

test("plans a trip from fixture", async ({ page }) => {
  await page.route("**/api/plan", (route) => route.fulfill({ json: plan }));
  await page.goto("/");
  await page.getByRole("button", { name: "Compare routes" }).click();
  await expect(page.getByText("route-1")).toBeVisible();
  await expect(page.getByText("route-3")).toBeVisible();
  await expect(page.getByText("Recommended")).toBeVisible();
  await expect(page.getByText("50 mi · High").first()).toBeVisible();
});

test("heatmap slider does not remount the map", async ({ page }) => {
  await page.route("**/api/plan", (route) => route.fulfill({ json: plan }));
  await page.goto("/");
  await page.getByRole("button", { name: "Compare routes" }).click();
  await page.waitForTimeout(500);
  const before = await page.evaluate(() => (window as unknown as { __mapMounts?: number }).__mapMounts ?? 0);
  await page.getByLabel("Forecast hour").fill("12");
  await page.getByRole("button", { name: "Rain" }).click();
  const after = await page.evaluate(() => (window as unknown as { __mapMounts?: number }).__mapMounts ?? 0);
  expect(after).toBe(before);
  expect(before).toBeGreaterThan(0);
});
