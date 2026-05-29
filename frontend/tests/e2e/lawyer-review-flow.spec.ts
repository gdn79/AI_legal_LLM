import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("E2E-003 lawyer review flow", async ({ page }) => {
  await loginAs(page, "lawyer@example.com");

  await page.goto("/cases/case-1004/pretension");
  await expect(page.getByRole("button", { name: /approve/i })).toHaveCount(0);

  await page.goto("/cases/case-1004/claim");
  await expect(page.getByText("source_id: 2")).toBeVisible();

  await page.goto("/cases/case-1004/lawyer-review");
  await expect(page.getByTestId("authority-check-list")).toBeVisible();
  await expect(page.getByText(/PASSED|allowed/i)).toBeVisible();
  await expect(page.getByTestId("claim-copy-proof-state")).toBeVisible();
  await expect(page.getByText(/source 2/i)).toBeVisible();
});
