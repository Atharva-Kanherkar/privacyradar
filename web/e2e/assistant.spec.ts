import { expect, test } from "@playwright/test";

test.describe("Assistant", () => {
  test("evidence stays quote-backed and the panel matches configuration", async ({
    page,
  }) => {
    await page.goto("/companies/signal");
    // Quotes are behind an expandable row; opening it must reveal the verbatim text.
    await page.locator("summary", { hasText: "Email address" }).first().click();
    await expect(
      page.getByText("We collect your email address to create an account.").first(),
    ).toBeVisible();

    const trigger = page.getByRole("button", { name: "Ask about this policy" });
    if ((await trigger.count()) > 0) {
      // A model key is configured: the chat opens as a sidebar with suggestions.
      await trigger.click();
      await expect(page.locator("#assistant-input")).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Do they sell or share my data?" }),
      ).toBeVisible();
    } else {
      // No model key (CI): the assistant stays off, says so, and renders no
      // question control at all.
      await expect(page.getByText("The cited assistant is off")).toBeVisible();
      await expect(page.getByLabel("Question about this company")).toHaveCount(0);
    }
  });
});
