import { expect, test } from "@playwright/test";

test.skip(process.env.LIVE_BROWSER !== "1", "set LIVE_BROWSER=1 to run against the local Docker app");

test.use({ baseURL: "http://127.0.0.1:8080" });

test("live docker trip shows three routes", async ({ page }) => {
  test.setTimeout(180000);
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));
  const started = Date.now();
  const responsePromise = page.waitForResponse((response) => response.url().includes("/api/plan"), { timeout: 150000 });
  await page.goto("/");
  await page.getByRole("button", { name: "Compare routes" }).click();
  const response = await responsePromise;
  const elapsed = Date.now() - started;
  expect(response.status(), "live plan status").toBe(200);
  const body = await response.json();
  expect(body.routes).toHaveLength(3);
  expect(body.recommended_route_id).toBe(body.routes[0].id);
  expect(body.heatmap[0].hours).toHaveLength(49);
  expect(body.routes[0].checkpoints.length).toBeGreaterThan(2);
  expect(body.routes[0].checkpoints[0].eta).toBeTruthy();
  await expect(page.getByText("Recommended")).toBeVisible();
  await page.getByRole("button", { name: /route-2/ }).click();
  await expect(page.getByRole("button", { name: /route-2/ })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Wind" }).click();
  await page.getByLabel("Forecast hour").fill("6");
  await page.getByRole("button", { name: "Rain" }).click();
  await page.getByRole("button", { name: "Snow" }).click();
  await expect(page.getByRole("button", { name: "Snow" })).toHaveAttribute("aria-pressed", "true");
  expect(consoleErrors, consoleErrors.join("\n")).toEqual([]);
  console.log(JSON.stringify({ live_browser_ms: elapsed, timings_ms: body.timings_ms }));
});
