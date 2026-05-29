import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("E2E-001 organization and authority flow", async ({ page }) => {
  await loginAs(page, "admin@example.com");

  await page.goto("/organizations");
  await expect(page.getByText("7701234567")).toBeVisible();

  await page.goto("/organizations/org-1");
  await expect(page.getByText(/^КПП: 770101001$/)).toBeVisible();
  await expect(page.getByText(/1027700123456/)).toBeVisible();
  await expect(page.getByText("VERIFIED", { exact: true })).toBeVisible();

  await page.goto("/organizations/org-1/employees");
  await expect(page.getByText("director@example.com")).toBeVisible();
  await expect(page.getByText("lawyer@example.com")).toBeVisible();

  await page.goto("/organizations/org-1/signatories");
  await expect(page.getByText("DIRECTOR")).toBeVisible();
  await expect(page.getByText("AUTHORIZED_EMPLOYEE")).toBeVisible();

  await page.goto("/organizations/org-1/powers-of-attorney");
  await expect(page.getByText("ACTIVE", { exact: true })).toBeVisible();
  await expect(page.getByText("EXPIRED", { exact: true })).toBeVisible();
  await expect(page.getByText("REVOKED", { exact: true })).toBeVisible();
});
