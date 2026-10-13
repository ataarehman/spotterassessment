import { expect, test } from "@playwright/test";

test.skip(process.env.LIVE_BROWSER !== "1", "set LIVE_BROWSER=1 to run against the local Docker app");

test.use({ baseURL: "http://127.0.0.1:8080" });

test("live docker trip shows three routes", async ({ page }) => {
  const started = Date.now();
  const responsePromise = page.waitForResponse((response) => response.url().includes("/api/plan"));
  await page.goto("/");
  await page.getByRole("button", { name: "Compare routes" }).click();
  const response = await responsePromise;
  const elapsed = Date.now() - started;
  expect(response.status(), "live plan status").toBe(200);
  const body = await response.json();
  expect(body.routes).toHaveLength(3);
  expect(body.heatmap[0].hours).toHaveLength(49);
  expect(body.timings_ms.total_ms).toBeGreaterThan(0);
  await expect(page.getByText("Recommended")).toBeVisible({ timeout: 5000 });
  await page.getByRole("button", { name: /route-2/ }).click();
  await page.getByLabel("Forecast hour").fill("6");
  await page.getByRole("button", { name: "Rain" }).click();
  await page.getByRole("button", { name: "Snow" }).click();
  console.log("live_browser_ms", elapsed, "api_total_ms", body.timings_ms.total_ms);
});
