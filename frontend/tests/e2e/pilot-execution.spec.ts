import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("DEMO-001 full UI path stays exportable", async ({ page }) => {
  await loginAs(page, "lawyer@example.com");

  await page.goto("/cases/case-1001/documents");
  await expect(page.getByText("contract.pdf")).toBeVisible();

  await page.goto("/cases/case-1001/facts");
  await expect(page.getByText("1 250 000")).toBeVisible();

  await page.goto("/cases/case-1001/pretension");
  await expect(page.getByText(/Approved pretension/i)).toBeVisible();

  await page.goto("/cases/case-1001/claim");
  await expect(page.getByText(/Approved claim/i)).toBeVisible();

  await page.goto("/cases/case-1001/lawyer-review");
  await expect(page.getByTestId("claim-copy-proof-state")).toContainText(/confirmed|подтвержден/i);
  await expect(page.getByTestId("export-package-button")).toBeEnabled();
  await page.getByTestId("export-package-button").click();
  await expect(page.getByText(/mock\/exports\/1001\.zip|Комплект сформирован/i)).toBeVisible();
});

test("DEMO-002 employee signatory happy path remains valid", async ({ page }) => {
  await loginAs(page, "lawyer@example.com");
  await page.goto("/cases/case-1004/lawyer-review");
  await expect(page.getByTestId("authority-check-list")).toContainText(/PASSED|allowed/i);
  await expect(page.getByTestId("export-package-button")).toBeEnabled();
});

test("DEMO-003 authority block path stays blocked", async ({ page }) => {
  await loginAs(page, "lawyer@example.com");
  await page.goto("/cases/case-1003/lawyer-review");
  await expect(page.getByTestId("authority-check-list")).toContainText(/blocked|failed/i);
  await expect(page.getByTestId("export-package-button")).toBeDisabled();
});

test("pilot feedback creation path works", async ({ page }) => {
  await loginAs(page, "lawyer@example.com");
  await page.goto("/cases/case-1003/feedback");
  await page.getByTestId("feedback-title").fill("Pilot note from UI");
  await page.getByTestId("feedback-submit").click();
  await expect(page.getByText("Feedback saved.")).toBeVisible();
});

test("pilot metrics visibility path works", async ({ page }) => {
  await loginAs(page, "admin@example.com");
  await page.goto("/pilot-metrics");
  await expect(page.getByTestId("pilot-metrics-page")).toBeVisible();
  await expect(page.getByText("Happy path cases")).toBeVisible();
  await expect(page.getByTestId("authority-invalid-case-1003")).toContainText("invalid: 1");
  await expect(page.getByTestId("pilot-report-recommendation")).toContainText(/go|no-go/i);
  await expect(page.getByTestId("pilot-report-unresolved")).toContainText("0");
});

test("timeline page shows key events in order", async ({ page }) => {
  await loginAs(page, "admin@example.com");
  await page.goto("/cases/case-1001/timeline");
  await expect(page.getByTestId("case-timeline-page")).toBeVisible();
  const events = page.getByTestId("timeline-event-list").locator(".list-item strong");
  await expect(events.nth(0)).toContainText("Case created");
});
