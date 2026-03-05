import { expect, test } from "@playwright/test";

import { loginViaUI, registerUser } from "./helpers";

test.describe("Authentication", () => {
  test("register new account and land on dashboard", async ({
    page,
    request,
  }) => {
    const ts = Date.now();
    const email = `e2e-reg-${ts}@test.com`;
    const username = `e2ereg${ts}`;

    await page.goto("/register");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Password", { exact: true }).fill("TestPass123!");
    await page.getByLabel("Confirm Password").fill("TestPass123!");
    await page.getByRole("button", { name: "Create account" }).click();

    await page.waitForURL("**/dashboard", { timeout: 10_000 });
    await expect(page.getByText("Welcome,")).toBeVisible({ timeout: 10_000 });
  });

  test("login with valid credentials", async ({ page, request }) => {
    const user = await registerUser(request);
    await loginViaUI(page, user.email, user.password);
    await expect(page.getByText("Welcome,")).toBeVisible({ timeout: 10_000 });
  });

  test("login with wrong password shows error", async ({ page, request }) => {
    const user = await registerUser(request);
    await page.goto("/login");
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Password").fill("WrongPassword!");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();

    await expect(page.locator(".text-red-600")).toBeVisible({ timeout: 5_000 });
  });

  test("logout redirects to login", async ({ page, request }) => {
    const user = await registerUser(request);
    await loginViaUI(page, user.email, user.password);

    await page.getByRole("button", { name: "Sign out" }).click();
    await page.waitForURL("**/login", { timeout: 5_000 });
  });

  test("unauthenticated user redirected to login", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForURL("**/login", { timeout: 5_000 });
  });
});
