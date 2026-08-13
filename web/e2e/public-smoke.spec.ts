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
    await expect(page.getByRole("link", { name: "Signal" })).toBeVisible();
    await expect(page.getByText("timeout")).not.toBeVisible();
    await expect(page.getByText("healthy").or(page.getByText("pending"))).toBeVisible();

    const companies = await request.get("/api/companies?q=signal");
    expect(companies.status()).toBe(200);
    const list = (await companies.json()) as Array<{
      slug: string;
      source_health: string;
      last_error?: string;
    }>;
    expect(list.some((row) => row.slug === "signal")).toBe(true);
    expect(JSON.stringify(list)).not.toMatch(/last_error/);
    expect(JSON.stringify(list)).not.toMatch(/postgresql:\/\//);

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
