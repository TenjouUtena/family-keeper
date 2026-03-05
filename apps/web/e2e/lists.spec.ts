import { expect, test } from "@playwright/test";

import { createFamily, createList, loginViaUI, registerUser } from "./helpers";

test.describe("Lists", () => {
  test("create grocery list via UI", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}/lists/new`);

    await page.getByLabel("List Name").fill("Weekly Groceries");
    await page.getByRole("button", { name: "Grocery" }).click();
    await page.getByRole("button", { name: "Create List" }).click();

    // Should redirect to list detail
    await expect(
      page.getByRole("heading", { name: "Weekly Groceries" }),
    ).toBeVisible({ timeout: 5_000 });
  });

  test("add single item to list", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(request, user.accessToken, family.id);
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}/lists/${list.id}`);
    await page.getByPlaceholder("Add an item...").fill("Milk");
    await page.getByRole("button", { name: "Add" }).click();

    await expect(page.getByText("Milk")).toBeVisible({ timeout: 5_000 });
  });

  test("add multiple items sequentially", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(request, user.accessToken, family.id);
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}/lists/${list.id}`);

    for (const item of ["Eggs", "Bread", "Butter"]) {
      await page.getByPlaceholder("Add an item...").fill(item);
      await page.getByRole("button", { name: "Add" }).click();
      await expect(page.getByText(item)).toBeVisible({ timeout: 5_000 });
    }
  });

  test("mark item as done", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(request, user.accessToken, family.id);
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}/lists/${list.id}`);

    // Add an item first
    await page.getByPlaceholder("Add an item...").fill("Test item");
    await page.getByRole("button", { name: "Add" }).click();
    await expect(page.getByText("Test item")).toBeVisible({ timeout: 5_000 });

    // Click the mark-as-done button
    await page.getByLabel("Mark as done").click();

    // Item should appear in completed section
    await expect(page.getByText(/Completed/)).toBeVisible({ timeout: 5_000 });
  });

  test("delete item from list", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(request, user.accessToken, family.id);
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}/lists/${list.id}`);

    // Add an item
    await page.getByPlaceholder("Add an item...").fill("Delete me");
    await page.getByRole("button", { name: "Add" }).click();
    await expect(page.getByText("Delete me")).toBeVisible({ timeout: 5_000 });

    // Delete it
    await page.getByLabel("Delete item").click();

    await expect(page.getByText("Delete me")).not.toBeVisible({
      timeout: 5_000,
    });
  });

  test("create chore list with photo requirement", async ({
    page,
    request,
  }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}/lists/new`);

    await page.getByLabel("List Name").fill("Chores");
    await page.getByRole("button", { name: "Chores" }).click();

    // Checkbox should appear for chore lists
    const photoCheckbox = page.getByLabel("Require photo proof");
    await expect(photoCheckbox).toBeVisible();
    await photoCheckbox.check();

    await page.getByRole("button", { name: "Create List" }).click();

    // Should show photo requirement badge
    await expect(page.getByText("Photo proof required")).toBeVisible({
      timeout: 5_000,
    });
  });
});
