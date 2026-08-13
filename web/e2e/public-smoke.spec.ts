import { expect, test } from "@playwright/test";

test.describe("public smoke", () => {
  test("home, catalog, company, about, feed, and health work without login", async ({
    page,
    request,
  }) => {
    const health = await request.get("/api/health");
    expect(health.status()).toBe(200);
    const payload = (await health.json()) as {
      status: string;
      database: string;
    };
    expect(payload.status).toBe("ok");
    expect(payload.database).toBe("connected");
    expect(JSON.stringify(payload)).not.toMatch(/postgresql:\/\//);
    expect(JSON.stringify(payload)).not.toMatch(/OPENAI/i);

    expect((await page.goto("/"))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "What they take. What just changed.",
    );
    await expect(page.getByRole("navigation")).toBeVisible();
    await expect(page.getByRole("link", { name: "Companies" })).toBeVisible();
    await expect(page.getByRole("link", { name: "About" })).toBeVisible();

    expect((await page.goto("/companies"))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1, name: "Catalog" })).toBeVisible();
    const signalRow = page.getByRole("row", { name: /Signal/ });
    await expect(signalRow).toBeVisible();
    await expect(signalRow.getByText(/^(healthy|pending|check delayed)$/)).toBeVisible();
    await expect(signalRow.getByText(/timeout|dns|Connection refused/i)).toHaveCount(0);

    const companies = await request.get("/api/companies?q=signal");
    expect(companies.status()).toBe(200);
    const list = (await companies.json()) as Array<{
      slug: string;
      source_health: string;
      last_error?: unknown;
    }>;
    const signal = list.find((row) => row.slug === "signal");
    expect(signal).toBeDefined();
    expect(["pending", "healthy", "degraded", "quarantined"]).toContain(
      signal?.source_health,
    );
    expect(signal && "last_error" in signal).toBe(false);
    expect(JSON.stringify(list)).not.toMatch(/postgresql:\/\//);
    expect(JSON.stringify(list)).not.toMatch(/Traceback|Error:/);

    const detail = await request.get("/api/companies/signal");
    expect(detail.status()).toBe(200);
    const companyJson = (await detail.json()) as {
      current_snapshot_id: string | null;
      region: string | null;
    };
    expect(companyJson.current_snapshot_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
    expect(companyJson.region).toBeTruthy();
    expect((await request.get("/api/companies/does-not-exist")).status()).toBe(404);
    expect(
      (await request.get("/api/changes/00000000-0000-0000-0000-000000000000")).status(),
    ).toBe(404);

    expect((await page.goto("/companies/signal"))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1, name: "Signal" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Current privacy policy" })).toBeVisible();
    await expect(page.getByText("Not yet verified. A missing or failed fetch is not an empty policy.")).toHaveCount(0);

    expect((await page.goto("/about"))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1, name: "About" })).toBeVisible();

    const feed = await request.get("/feed.xml");
    expect(feed.status()).toBe(200);
    expect(feed.headers()["content-type"] ?? "").toMatch(/xml/);

    const missing = await request.get("/companies/this-slug-does-not-exist");
    expect(missing.status()).toBe(404);
  });

  test("home heading and nav remain visible at 320px", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    expect((await page.goto("/"))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("link", { name: "Companies" })).toBeVisible();
    await expect(page.getByRole("link", { name: "About" })).toBeVisible();
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
  });
});
