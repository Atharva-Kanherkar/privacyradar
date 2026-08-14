import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

function uniqueEmail(label: string): string {
  return `${label}-${Date.now()}-${Math.random().toString(16).slice(2)}@fixtures.privacyradar.test`;
}

function privacyradarBin(): string {
  const fromVenv = path.resolve(__dirname, "../../worker/.venv/bin/privacyradar");
  if (fs.existsSync(fromVenv)) {
    return fromVenv;
  }
  return "privacyradar";
}

function runWorker(args: string[]): string {
  return execFileSync(privacyradarBin(), args, {
    encoding: "utf8",
    env: {
      ...process.env,
      AUTH_DELIVERY: "fixture",
      NOTIFY_PROVIDER: "fake",
      AUTH_SECRET: process.env.AUTH_SECRET || "ci-test-auth-secret-issue-10",
    },
  });
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

test.describe("Change alerts", () => {
  test("/radar/settings without a session redirects to login", async ({ page }) => {
    await page.goto("/radar/settings");
    await expect(page).toHaveURL(/\/login/);
  });

  test("tampered unsubscribe token is invalid", async ({ page }) => {
    await page.goto("/unsubscribe?token=not-a-real-token");
    await expect(
      page.getByRole("heading", { name: "This unsubscribe link is not valid" }),
    ).toBeVisible();
  });

  test("published change sends one fake email and unsubscribe stops the next", async ({
    page,
    request,
  }) => {
    const email = uniqueEmail("alert");
    await signIn(page, request, email);
    await page.goto("/companies/signal");
    await page.getByRole("button", { name: "Watch" }).click();
    await expect(page.getByRole("button", { name: "Watching" })).toBeVisible();

    await page.goto("/radar/settings");
    await page.getByLabel("Weekly digest of published material changes").check();
    await page.getByRole("button", { name: "Save alert settings" }).click();
    await expect(
      page.getByLabel("Weekly digest of published material changes"),
    ).toBeChecked();
    await page.getByLabel("Email me when a published material change lands").check();
    await page.getByRole("button", { name: "Save alert settings" }).click();
    await expect(
      page.getByLabel("Email me when a published material change lands"),
    ).toBeChecked();

    runWorker([
      "fixture-publish-change",
      "--slug",
      "signal",
      "--headline",
      "E2E_ALERT_HEADLINE",
    ]);
    runWorker(["notify-fanout"]);
    runWorker(["notify-deliver"]);

    const inbox = await request.get(
      `/api/test/notify-inbox?email=${encodeURIComponent(email)}`,
    );
    expect(inbox.status()).toBe(200);
    const mail = (await inbox.json()) as { subject: string; body_text: string };
    expect(mail.subject).toContain("E2E_ALERT_HEADLINE");
    expect(mail.body_text).toContain("E2E_ALERT_HEADLINE");
    expect(mail.body_text).toContain("/changes/");
    expect(mail.body_text).not.toContain("UNPUBLISHED_FIXTURE_HEADLINE");
    const match = mail.body_text.match(/http:\/\/[^\s]+\/unsubscribe\?token=[^\s]+/);
    expect(match).toBeTruthy();
    const unsub = match![0];

    await page.goto(unsub);
    await page.getByRole("button", { name: "Confirm unsubscribe" }).click();
    await expect(page.getByRole("status")).toContainText("will not send further");

    runWorker(["notify-deliver"]);
    const again = await request.get(
      `/api/test/notify-inbox?email=${encodeURIComponent(email)}`,
    );
    expect(again.status()).toBe(200);
    const second = (await again.json()) as { subject: string };
    expect(second.subject).toBe(mail.subject);
  });
});
