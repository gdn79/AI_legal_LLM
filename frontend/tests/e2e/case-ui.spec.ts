import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("E2E-002 case happy path UI skeleton", async ({ page }) => {
  await loginAs(page, "lawyer@example.com");
  await page.goto("/cases/case-1001/lawyer-review");
  await expect(page.getByRole("link", { name: "Documents" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Facts" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Pretension" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Claim" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Lawyer review" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Feedback", exact: true })).toBeVisible();
  await expect(page.getByTestId("authority-check-list")).toBeVisible();
});
