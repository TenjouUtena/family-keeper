import { expect, test } from "@playwright/test";

import {
  createFamily,
  createInviteCode,
  loginViaUI,
  registerUser,
} from "./helpers";

test.describe("Family management", () => {
  test("create a family via UI", async ({ page, request }) => {
    const user = await registerUser(request);
    await loginViaUI(page, user.email, user.password);

    await page.goto("/families/new");

    await page.getByLabel("Family Name").fill("The Smiths");
    await page.getByRole("button", { name: "Create Family" }).click();

    // Should redirect to family detail
    await expect(page.getByRole("heading", { name: "The Smiths" })).toBeVisible({
      timeout: 5_000,
    });
  });

  test("generate invite code", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken, "Invite Family");
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}`);
    await page.getByRole("button", { name: "Generate Invite Code" }).click();

    // Invite code should be displayed (8 chars, monospace)
    await expect(page.locator(".font-mono.tracking-widest")).toBeVisible({
      timeout: 5_000,
    });
  });

  test("second user joins family via invite code", async ({
    page,
    request,
  }) => {
    // User 1 creates family + invite
    const user1 = await registerUser(request);
    const family = await createFamily(request, user1.accessToken, "Join Family");
    const invite = await createInviteCode(
      request,
      user1.accessToken,
      family.id,
    );

    // User 2 joins
    const user2 = await registerUser(request);
    await loginViaUI(page, user2.email, user2.password);

    await page.goto("/families/join");
    await page.getByLabel("Invite Code").fill(invite.code);
    await page.getByRole("button", { name: "Join Family" }).click();

    // Should redirect to family detail
    await expect(
      page.getByRole("heading", { name: "Join Family" }),
    ).toBeVisible({ timeout: 5_000 });
  });

  test("family members listed with roles", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(request, user.accessToken);
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}`);

    // Creator should be listed as a member
    await expect(page.getByText(user.username)).toBeVisible();
    // Should show parent role
    await expect(page.getByText("parent", { exact: false })).toBeVisible();
  });

  test("update family name", async ({ page, request }) => {
    const user = await registerUser(request);
    const family = await createFamily(
      request,
      user.accessToken,
      "Old Name",
    );
    await loginViaUI(page, user.email, user.password);

    await page.goto(`/families/${family.id}/settings`);

    const nameInput = page.getByLabel("Family Name");
    await nameInput.clear();
    await nameInput.fill("New Name");
    await page.getByRole("button", { name: "Save Changes" }).click();

    // Navigate back and verify
    await page.goto(`/families/${family.id}`);
    await expect(
      page.getByRole("heading", { name: "New Name" }),
    ).toBeVisible({ timeout: 5_000 });
  });
});
