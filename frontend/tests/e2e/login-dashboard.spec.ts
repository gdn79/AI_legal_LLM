import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("E2E-001 login and dashboard", async ({ page }) => {
  await loginAs(page, "manager@example.com");
  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard-loaded")).toBeVisible();
  await expect(page).toHaveURL(/\/dashboard$/);
});
