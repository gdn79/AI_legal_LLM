import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("E2E-005 court import mock flow", async ({ page }) => {
  await loginAs(page, "admin@example.com");

  await page.goto("/court-import");
  await expect(page.getByTestId("court-import-form")).toBeVisible();
  await page.getByRole("button", { name: /import job/i }).click();
  await expect(page.getByRole("link", { name: /Job #/ }).first()).toBeVisible();

  await page.getByRole("link", { name: /Job #/ }).first().click();
  await expect(page).toHaveURL(/\/court-import\/.+$/);
  await page.goto("/external-court-cases/1");
  await expect(page).toHaveURL(/\/external-court-cases\/.+$/);
  await expect(page.getByTestId("linked-internal-case")).toContainText("1004");
});

test("E2E-006 audit visibility", async ({ page }) => {
  await loginAs(page, "admin@example.com");

  await page.goto("/audit");
  await expect(page.getByTestId("audit-loaded")).toBeVisible();
  await expect(page.getByText("organization_created")).toBeVisible();
  await expect(page.getByText("power_of_attorney_created")).toBeVisible();
  await expect(page.getByText("claim_approved")).toBeVisible();
  await expect(page.getByText("postal_proof_uploaded")).toBeVisible();
  await expect(page.getByText("court_import_job_created")).toBeVisible();
  await expect(page.getByText("case_exported")).toBeVisible();
  await expect(page.getByText("[REDACTED]")).toBeVisible();
  await expect(page.getByText("super-secret-token")).toHaveCount(0);
});
