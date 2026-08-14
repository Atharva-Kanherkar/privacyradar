import { expect, test } from "@playwright/test";

const PUBLISHED_CHANGE_ID = "1f8ffff1-5bd2-5137-a95a-9464388eb5d8";
const UNPUBLISHED_CHANGE_ID = "e5bb658e-b8ef-5910-a579-7ff1ba68197b";

test.describe("public smoke", () => {
  test("home, catalog, company, methodology, feed, and health work without login", async ({
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
      "What do the services you use disclose about your data?",
    );
    await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Companies" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "How it works" })).toBeVisible();
    await expect(page.getByText("UNPUBLISHED_FIXTURE_HEADLINE")).toHaveCount(0);
    await expect(page.getByText("PUBLISHED_FIXTURE_HEADLINE")).toBeVisible();

    await page.getByLabel("Search a company").fill("signal");
    await page.getByRole("button", { name: "Search" }).click();
    await expect(page).toHaveURL(/\/companies\?q=signal/i);
    await page.getByRole("link", { name: "Signal" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Signal" })).toBeVisible();
    await page.locator("summary", { hasText: "Email address" }).first().click();
    await expect(
      page.getByText("We collect your email address to create an account.").first(),
    ).toBeVisible();

    expect((await page.goto("/companies"))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1, name: "Catalog" })).toBeVisible();
    const signalCard = page.getByRole("link", { name: /Signal/ }).first();
    await expect(signalCard).toBeVisible();
    await expect(signalCard.getByText(/^(healthy|pending|check delayed)$/)).toBeVisible();
    await expect(signalCard.getByText(/timeout|dns|Connection refused/i)).toHaveCount(0);

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
    await expect(
      page.getByText("Not yet verified. A missing or failed fetch is not an empty policy."),
    ).toHaveCount(0);
    await expect(page.getByText("UNPUBLISHED_FIXTURE_HEADLINE")).toHaveCount(0);

    expect((await page.goto(`/changes/${PUBLISHED_CHANGE_ID}`))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "PUBLISHED_FIXTURE_HEADLINE",
    );
    expect((await page.goto(`/changes/${UNPUBLISHED_CHANGE_ID}`))?.status()).toBe(404);

    expect((await page.goto("/methodology"))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1, name: "Methodology" })).toBeVisible();

    const feed = await request.get("/feed.xml");
    expect(feed.status()).toBe(200);
    expect(feed.headers()["content-type"] ?? "").toMatch(/xml/);
    const feedText = await feed.text();
    expect(feedText).not.toContain("UNPUBLISHED_FIXTURE_HEADLINE");
    expect(feedText).toContain("PUBLISHED_FIXTURE_HEADLINE");

    const sitemap = await request.get("/sitemap.xml");
    expect(sitemap.status()).toBe(200);
    expect(await sitemap.text()).toContain("/methodology");

    const missing = await request.get("/companies/this-slug-does-not-exist");
    expect(missing.status()).toBe(404);
  });

  test("skip link is the first focusable control", async ({ page }) => {
    await page.goto("/");
    await page.locator("body").press("Tab");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  });

  test("home heading remains visible at 320px", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    expect((await page.goto("/"))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText("Menu")).toBeVisible();
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 8);
  });
});
