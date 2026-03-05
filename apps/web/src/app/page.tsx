"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuthStore } from "@/stores/auth-store";

export default function Home() {
  const { isAuthenticated, isHydrated } = useAuthStore();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    useAuthStore.getState().hydrate().then(() => setReady(true));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold tracking-tight text-indigo-600">
        Family Keeper
      </h1>
      <p className="mt-4 text-lg text-gray-600">
        Manage your family&apos;s shared ecosystem
      </p>
      {ready && isHydrated && (
        <div className="mt-8">
          {isAuthenticated ? (
            <Link
              href="/dashboard"
              className="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-500"
            >
              Go to Dashboard
            </Link>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-500"
            >
              Sign in
            </Link>
          )}
        </div>
      )}
    </main>
  );
}
