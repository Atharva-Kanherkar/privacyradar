import { expect, test } from "@playwright/test";

test.describe("Cited assistant", () => {
  test("stays off and does not invent an answer", async ({ page }) => {
    await page.goto("/companies/signal");
    await expect(
      page.getByText("We collect your email address to create an account."),
    ).toBeVisible();
    await expect(page.getByText("The cited assistant is off")).toBeVisible();
    await expect(page.getByLabel("Question about this company")).toHaveCount(0);
  });
});
