import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("E2E-002 case document flow", async ({ page }) => {
  await loginAs(page, "initiator@example.com");

  await page.goto("/cases/case-1001/documents");
  await expect(page.getByText("contract.pdf", { exact: true })).toBeVisible();
  await expect(page.getByText("act.pdf", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /download/i })).toHaveCount(0);

  await page.goto("/cases/case-1001/facts");
  await expect(page.getByText("123/24")).toBeVisible();
  await expect(page.getByText("1 250 000")).toBeVisible();
});
