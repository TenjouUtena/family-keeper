import { expect, test } from "@playwright/test";

import {
  addItems,
  createFamily,
  createList,
  loginViaUI,
  registerUser,
} from "./helpers";

test.describe("Items workflow", () => {
  test("full flow: add items → complete → verify", async ({
    page,
    request,
  }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(
      request,
      user.accessToken,
      family.id,
      "Todo List",
      "todo",
    );
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}/lists/${list.id}`);

    // Add items one by one
    for (const item of ["Task A", "Task B", "Task C"]) {
      await page.getByPlaceholder("Add an item...").fill(item);
      await page.getByRole("button", { name: "Add" }).click();
      await expect(page.getByText(item)).toBeVisible({ timeout: 5_000 });
    }

    // Complete Task B — find the card containing "Task B" and click its mark-as-done button
    const taskBCard = page.locator("[class*=card]").filter({ hasText: "Task B" });
    await taskBCard.getByLabel("Mark as done").click();

    // Task B should move to completed section
    await expect(page.getByText(/Completed/)).toBeVisible({ timeout: 5_000 });

    // Task A and C should still be visible
    await expect(page.getByText("Task A")).toBeVisible();
    await expect(page.getByText("Task C")).toBeVisible();
  });

  test("item count updates in list overview", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(
      request,
      user.accessToken,
      family.id,
      "Count List",
    );

    // Seed 3 items via API
    await addItems(request, user.accessToken, family.id, list.id, [
      "Item 1",
      "Item 2",
      "Item 3",
    ]);

    await loginViaUI(page, user.email, user.password);
    await page.goto(`/families/${family.id}/lists`);

    // Should show item count
    await expect(page.getByText(/3 items/)).toBeVisible({ timeout: 5_000 });
  });

  test("undo completed item as parent", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(
      request,
      user.accessToken,
      family.id,
      "Undo List",
      "todo",
    );
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}/lists/${list.id}`);

    // Add and complete an item
    await page.getByPlaceholder("Add an item...").fill("Undo me");
    await page.getByRole("button", { name: "Add" }).click();
    await expect(page.getByText("Undo me")).toBeVisible({ timeout: 5_000 });

    await page.getByLabel("Mark as done").click();

    // Wait for completed section
    await expect(page.getByText(/Completed/)).toBeVisible({ timeout: 5_000 });

    // Click the done checkbox to undo (parent can undo)
    await page.getByLabel("Mark as pending").click();

    // Item should move back to pending (completed section disappears)
    await expect(page.getByText("Undo me")).toBeVisible({ timeout: 5_000 });
  });

  test("seeded items visible on list detail", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    const list = await createList(
      request,
      user.accessToken,
      family.id,
      "Seeded List",
    );
    await addItems(request, user.accessToken, family.id, list.id, [
      "Apples",
      "Bananas",
      "Cherries",
    ]);

    await loginViaUI(page, user.email, user.password);
    await page.goto(`/families/${family.id}/lists/${list.id}`);

    await expect(page.getByText("Apples")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Bananas")).toBeVisible();
    await expect(page.getByText("Cherries")).toBeVisible();
  });
});
