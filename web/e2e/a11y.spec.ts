import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const routes = [
  "/",
  "/companies",
  "/companies/signal",
  "/changes",
  "/methodology",
  "/login",
];

test.describe("axe", () => {
  for (const route of routes) {
    test(`no serious or critical violations on ${route}`, async ({ page }) => {
      expect((await page.goto(route))?.status()).toBe(200);
      const results = await new AxeBuilder({ page }).analyze();
      const blocking = results.violations.filter(
        (violation) => violation.impact === "serious" || violation.impact === "critical",
      );
      expect(blocking).toEqual([]);
    });
  }

  test("home has no serious axe violations at 320px", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    expect((await page.goto("/"))?.status()).toBe(200);
    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );
    expect(blocking).toEqual([]);
  });
});
