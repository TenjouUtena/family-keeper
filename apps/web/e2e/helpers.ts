import type { APIRequestContext, Page } from "@playwright/test";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let userCounter = 0;

/**
 * Register a unique test user via the API.
 * Returns credentials + access token for API seeding.
 */
export async function registerUser(request: APIRequestContext) {
  const id = ++userCounter;
  const ts = Date.now();
  const email = `e2e-user-${id}-${ts}@test.com`;
  const username = `e2euser${id}${ts}`;
  const password = "TestPass123!";

  const res = await request.post(`${API}/v1/auth/register`, {
    data: { email, username, password },
  });

  if (!res.ok()) {
    throw new Error(
      `registerUser failed: ${res.status()} ${await res.text()}`,
    );
  }

  const body = await res.json();
  return {
    email,
    username,
    password,
    accessToken: body.access_token as string,
    refreshToken: body.refresh_token as string,
  };
}

/**
 * Log in through the UI (fills form + submits).
 * Waits for redirect to dashboard.
 */
export async function loginViaUI(
  page: Page,
  email: string,
  password: string,
) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("**/dashboard", { timeout: 10_000 });
}

/**
 * Create a family via the API. Returns family object.
 */
export async function createFamily(
  request: APIRequestContext,
  token: string,
  name = "Test Family",
) {
  const res = await request.post(`${API}/v1/families`, {
    data: { name },
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok()) {
    throw new Error(
      `createFamily failed: ${res.status()} ${await res.text()}`,
    );
  }

  return res.json();
}

/**
 * Create a list via the API. Returns list object.
 */
export async function createList(
  request: APIRequestContext,
  token: string,
  familyId: string,
  name = "Test List",
  listType = "grocery",
) {
  const res = await request.post(`${API}/v1/families/${familyId}/lists`, {
    data: { name, list_type: listType },
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok()) {
    throw new Error(
      `createList failed: ${res.status()} ${await res.text()}`,
    );
  }

  return res.json();
}

/**
 * Bulk add items to a list via the API.
 */
export async function addItems(
  request: APIRequestContext,
  token: string,
  familyId: string,
  listId: string,
  items: string[],
) {
  const res = await request.post(
    `${API}/v1/families/${familyId}/lists/${listId}/items`,
    {
      data: { items: items.map((content) => ({ content })) },
      headers: { Authorization: `Bearer ${token}` },
    },
  );

  if (!res.ok()) {
    throw new Error(`addItems failed: ${res.status()} ${await res.text()}`);
  }

  return res.json();
}

/**
 * Generate an invite code for a family via the API.
 */
export async function createInviteCode(
  request: APIRequestContext,
  token: string,
  familyId: string,
) {
  const res = await request.post(`${API}/v1/families/${familyId}/invites`, {
    data: {},
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok()) {
    throw new Error(
      `createInviteCode failed: ${res.status()} ${await res.text()}`,
    );
  }

  return res.json();
}
