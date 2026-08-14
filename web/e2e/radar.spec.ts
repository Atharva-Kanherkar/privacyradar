import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

function uniqueEmail(label: string): string {
  return `${label}-${Date.now()}-${Math.random().toString(16).slice(2)}@fixtures.privacyradar.test`;
}

async function signIn(page: Page, request: APIRequestContext, email: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Email me a link" }).click();
  await expect(page.getByRole("status")).toContainText("If that address can be used");
  const inbox = await request.get(
    `/api/test/magic-inbox?email=${encodeURIComponent(email)}`,
  );
  expect(inbox.status()).toBe(200);
  const payload = (await inbox.json()) as { url: string };
  await page.goto(payload.url);
}

test.describe("My Radar", () => {
  test("/radar without a session redirects to login", async ({ page }) => {
    await page.goto("/radar");
    await expect(page).toHaveURL(/\/login/);
  });

  test("anonymous watch resumes after magic link and unfollow hides the feed", async ({
    page,
    request,
  }) => {
    await page.goto("/companies/signal");
    await page.getByRole("link", { name: "Watch" }).click();
    await expect(page).toHaveURL(/\/login/);
    const email = uniqueEmail("radar");
    await page.getByLabel("Email").fill(email);
    await page.getByRole("button", { name: "Email me a link" }).click();
    await expect(page.getByRole("status")).toContainText(
      "If that address can be used, we sent a link.",
    );
    const inbox = await request.get(
      `/api/test/magic-inbox?email=${encodeURIComponent(email)}`,
    );
    expect(inbox.status()).toBe(200);
    const payload = (await inbox.json()) as { url: string };
    expect(payload.url).toBeTruthy();
    await page.goto(payload.url);
    await expect(page).toHaveURL(/\/companies\/signal/);
    await expect(page.getByRole("button", { name: "Watching" })).toBeVisible();

    await page.goto("/radar");
    await expect(page.getByRole("heading", { level: 1, name: "My Radar" })).toBeVisible();
    await expect(page.getByText("PUBLISHED_FIXTURE_HEADLINE")).toBeVisible();
    await expect(page.getByText("UNPUBLISHED_FIXTURE_HEADLINE")).toHaveCount(0);

    await page.goto("/radar/watching");
    await page.getByRole("button", { name: "Watching" }).click();
    await page.goto("/radar");
    await expect(page.getByText("PUBLISHED_FIXTURE_HEADLINE")).toHaveCount(0);
  });

  test("signed-in follow from the company page", async ({ page, request }) => {
    const email = uniqueEmail("signed-watch");
    await signIn(page, request, email);
    await page.goto("/companies/signal");
    await page.getByRole("button", { name: "Watch" }).click();
    await expect(page.getByRole("button", { name: "Watching" })).toBeVisible();
    await page.goto("/radar");
    await expect(page.getByText("PUBLISHED_FIXTURE_HEADLINE")).toBeVisible();
  });
});
