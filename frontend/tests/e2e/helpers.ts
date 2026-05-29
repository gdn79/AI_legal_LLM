import type { Page } from "@playwright/test";

export async function loginAs(page: Page, email: string) {
  await page.goto("/login");
  await page.getByTestId("login-email").fill(email);
  await page.getByTestId("login-password").fill("ChangeMe123!");
  await page.getByTestId("login-submit").click();
  await page.waitForURL("**/cases");
}
