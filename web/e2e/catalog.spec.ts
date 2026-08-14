import { expect, test } from "@playwright/test";

test.describe("Catalog requests", () => {
  test("nomination is requested, not monitored", async ({ page }) => {
    await page.goto("/companies/request");
    await expect(page.getByText("requested, not monitored")).toBeVisible();
    await page.getByLabel("Company name").fill("Example Co");
    await page.getByLabel("Official website").fill("https://example-nominate.test");
    await page.getByRole("button", { name: "Submit request" }).click();
    await expect(page.getByRole("status")).toContainText("not monitored yet");
  });

  test("duplicate website against Signal is not a crawl promise", async ({ page }) => {
    await page.goto("/companies/request");
    await page.getByLabel("Company name").fill("Signal again");
    await page.getByLabel("Official website").fill("https://signal.org");
    await page.getByRole("button", { name: "Submit request" }).click();
    await expect(page.getByRole("status")).toContainText("already in the catalog");
  });
});
