import { expect, test } from "@playwright/test";

test.describe("Comparisons", () => {
  test("Signal and Proton compare on a shareable URL without a score", async ({
    page,
    request,
  }) => {
    await page.goto("/compare");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Compare companies");
    await page.getByRole("checkbox", { name: "Signal" }).check();
    await page.getByRole("checkbox", { name: "Proton" }).check();
    await page.getByRole("button", { name: "Compare" }).click();
    await expect(page).toHaveURL(/\/compare\?companies=/);
    expect(page.url()).toMatch(/signal/);
    expect(page.url()).toMatch(/proton/);
    await expect(page.getByText("Not found in evidence").first()).toBeVisible();
    await expect(page.getByText("overall score")).toHaveCount(0);
    await expect(page.getByRole("table")).toBeVisible();
    await page.getByRole("link", { name: "Open evidence" }).first().click();
    await expect(page).toHaveURL(/\/companies\/(signal|proton)/);
    await expect(page.getByText(/We collect your email|advertising partners/)).toBeVisible();

    const api = await request.get("/api/compare?companies=signal,proton");
    expect(api.status()).toBe(200);
    const payload = (await api.json()) as {
      status: string;
      score?: unknown;
      dimensions: unknown;
    };
    expect(payload.status).toBe("comparable");
    expect(payload).not.toHaveProperty("score");
    expect(JSON.stringify(payload)).not.toMatch(/candidate_claims|extraction_runs/);
    expect(JSON.stringify(payload)).not.toMatch(/UNPUBLISHED_FIXTURE_HEADLINE/);
  });
});
