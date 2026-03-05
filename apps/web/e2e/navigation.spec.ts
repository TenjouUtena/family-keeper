import { expect, test } from "@playwright/test";

import { createFamily, createList, loginViaUI, registerUser } from "./helpers";

test.describe("Navigation", () => {
  test("bottom nav links work", async ({ page, request }) => {
    const user = await registerUser(request);
    await loginViaUI(page, user.email, user.password);

    // Should be on dashboard
    await expect(page).toHaveURL(/\/dashboard/);

    // Click Family tab
    await page.getByRole("link", { name: "Family" }).click();
    await expect(page).toHaveURL(/\/families$/);

    // Click Home tab
    await page.getByRole("link", { name: "Home" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("breadcrumb navigation from list detail", async ({
    page,
    request,
  }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(request, user.accessToken, family.id);
    await loginViaUI(page, user.email, user.password);

    // Navigate to list detail
    await page.goto(`/families/${family.id}/lists/${list.id}`);
    await expect(
      page.getByRole("heading", { name: list.name }),
    ).toBeVisible({ timeout: 5_000 });

    // Click back breadcrumb
    await page.getByRole("link", { name: /← Lists/ }).click();
    await expect(page).toHaveURL(
      new RegExp(`/families/${family.id}/lists$`),
    );
  });

  test("deep link to list detail works when authenticated", async ({
    page,
    request,
  }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(request, user.accessToken, family.id);
    await loginViaUI(page, user.email, user.password);

    // Navigate directly to a list URL
    await page.goto(`/families/${family.id}/lists/${list.id}`);
    await expect(
      page.getByRole("heading", { name: list.name }),
    ).toBeVisible({ timeout: 5_000 });
  });
});
