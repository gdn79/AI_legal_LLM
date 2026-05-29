import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("E2E-004 court package gate is visible in UI", async ({ page }) => {
  await loginAs(page, "lawyer@example.com");

  await page.goto("/cases/case-1003/lawyer-review");
  await expect(page.getByTestId("claim-copy-proof-state")).toContainText("Нет подтвержденного доказательства");
  await expect(page.getByTestId("export-package-button")).toBeDisabled();

  await page.goto("/cases/case-1004/lawyer-review");
  await expect(page.getByTestId("claim-copy-proof-state")).toContainText("подтверждено");
  await expect(page.getByTestId("export-package-button")).toBeEnabled();
});
