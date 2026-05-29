import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("E2E-003 non-admin cannot access integration settings", async ({ page }) => {
  await loginAs(page, "manager@example.com");
  await page.goto("/settings/russian-post");
  await expect(page.getByTestId("integration-settings-forbidden")).toBeVisible();
});

test("E2E-003 admin can access integration settings", async ({ page }) => {
  await loginAs(page, "admin@example.com");
  await page.goto("/settings/russian-post");
  await expect(page.getByTestId("integration-settings-loaded")).toBeVisible();
  await expect(page.getByText("RUSSIAN_POST_MODE")).toBeVisible();
});
