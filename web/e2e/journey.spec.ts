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

test.describe("Free-core journey", () => {
  test("browse, evidence, auth, follow, alert, unsubscribe, delete", async ({
    page,
    request,
  }) => {
    expect((await page.goto("/"))?.status()).toBe(200);
    await page.goto("/companies/signal");
    await expect(
      page.getByText("We collect your email address to create an account."),
    ).toBeVisible();
    await expect(page.getByText("The cited assistant is off")).toBeVisible();

    const email = uniqueEmail("journey17");
    await signIn(page, request, email);
    await page.goto("/companies/signal");
    await page.getByRole("button", { name: "Watch" }).click();
    await expect(page.getByRole("button", { name: "Watching" })).toBeVisible();
    await page.goto("/radar/settings");
    await page.getByLabel("Email me when a published material change lands").check();
    await page.getByRole("button", { name: "Save alert settings" }).click();

    runWorker([
      "fixture-publish-change",
      "--slug",
      "signal",
      "--headline",
      "E2E_JOURNEY_HEADLINE",
    ]);
    runWorker(["notify-fanout"]);
    runWorker(["notify-deliver"]);

    const inbox = await request.get(
      `/api/test/notify-inbox?email=${encodeURIComponent(email)}`,
    );
    expect(inbox.status()).toBe(200);
    const mail = (await inbox.json()) as { subject: string; body_text: string };
    expect(mail.subject).toContain("E2E_JOURNEY_HEADLINE");
    const match = mail.body_text.match(/http:\/\/[^\s]+\/unsubscribe\?token=[^\s]+/);
    expect(match).toBeTruthy();
    await page.goto(match![0]);
    await page.getByRole("button", { name: "Confirm unsubscribe" }).click();
    await expect(page.getByRole("status")).toContainText("will not send further");

    await page.goto("/account");
    await page.getByLabel("Type DELETE to remove this account").fill("DELETE");
    await page.getByRole("button", { name: "Delete account" }).click();
    await expect(page).toHaveURL(/\/login/);
  });
});
