import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const PUBLIC_COPY = "If that address can be used, we sent a link.";

function uniqueEmail(label: string): string {
  return `${label}-${Date.now()}-${Math.random().toString(16).slice(2)}@fixtures.privacyradar.test`;
}

async function requestMagicLink(page: Page, email: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Email me a link" }).click();
  await expect(page.getByRole("status")).toHaveText(PUBLIC_COPY);
}

async function inboxUrl(request: APIRequestContext, email: string): Promise<string> {
  const inbox = await request.get(
    `/api/test/magic-inbox?email=${encodeURIComponent(email)}`,
  );
  expect(inbox.status()).toBe(200);
  const payload = (await inbox.json()) as { url: string };
  expect(payload.url).toMatch(/^\/api\/auth\/magic-link\/verify\?/);
  expect(payload.url).not.toContain("https://");
  return payload.url;
}

test.describe("consumer auth", () => {
  test("anonymous home and catalog still work", async ({ page }) => {
    expect((await page.goto("/"))?.status()).toBe(200);
    await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "What do the services you use disclose about your data?",
    );
    expect((await page.goto("/companies"))?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1, name: "Catalog" })).toBeVisible();
  });

  test("magic link login, region, export, and delete", async ({ page, request }) => {
    const email = uniqueEmail("journey");
    await requestMagicLink(page, email);
    const url = await inboxUrl(request, email);
    await page.goto(url);
    await expect(page).toHaveURL(/\/account/);
    await expect(page.getByRole("heading", { level: 1, name: "Account" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Account" }).first()).toBeVisible();

    await page.getByLabel("Policy region").selectOption("US");
    await page.getByRole("button", { name: "Save region" }).click();
    await expect(page.getByLabel("Policy region")).toHaveValue("US");

    const exported = await page.request.get("/account/export");
    expect(exported.status()).toBe(200);
    const body = (await exported.json()) as {
      profile: { region: string };
      sessions: Array<Record<string, unknown>>;
    };
    expect(body.profile.region).toBe("US");
    expect(JSON.stringify(body)).not.toMatch(/"token"/);
    expect(JSON.stringify(body)).not.toMatch(/AUTH_SECRET/);

    await page.getByLabel("Type DELETE to remove this account").fill("DELETE");
    await page.getByRole("button", { name: "Delete account" }).click();
    await expect(page).toHaveURL(/\/login/);
    expect((await page.goto("/account"))?.status()).toBe(200);
    await expect(page).toHaveURL(/\/login/);
    expect((await page.request.get("/account/export")).status()).toBe(401);
  });

  test("replaying a magic link does not create a second session", async ({
    browser,
    page,
    request,
  }) => {
    const email = uniqueEmail("replay");
    await requestMagicLink(page, email);
    const url = await inboxUrl(request, email);
    await page.goto(url);
    await expect(page).toHaveURL(/\/account/);

    const isolated = await browser.newContext();
    const other = await isolated.newPage();
    await other.goto(url);
    expect((await other.goto("/account"))?.status()).toBe(200);
    await expect(other).toHaveURL(/\/login/);
    await isolated.close();
  });

  test("open redirect callback stays on origin", async ({ page }) => {
    const response = await page.goto(
      "/api/auth/magic-link/verify?token=deadbeef&callbackURL=https://evil.test",
    );
    expect(response?.url() ?? page.url()).not.toContain("evil.test");
    expect(new URL(page.url()).hostname).toMatch(/127\.0\.0\.1|localhost/);
  });

  test("magic link JSON does not reveal whether the email exists", async ({
    page,
    request,
  }) => {
    const known = uniqueEmail("known");
    const unknown = uniqueEmail("unknown");
    await requestMagicLink(page, known);
    const url = await inboxUrl(request, known);
    await page.goto(url);
    await expect(page).toHaveURL(/\/account/);
    const first = await request.post("/api/auth/sign-in/magic-link", {
      data: { email: known, callbackURL: "/account" },
    });
    const second = await request.post("/api/auth/sign-in/magic-link", {
      data: { email: unknown, callbackURL: "/account" },
    });
    expect(first.status()).toBe(second.status());
    expect(await first.text()).toBe(await second.text());
    expect(await first.text()).not.toContain(known);
    expect(await second.text()).not.toContain("not found");
  });
});
