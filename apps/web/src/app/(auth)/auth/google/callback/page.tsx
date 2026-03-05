"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";

function GoogleCallbackInner() {
  const searchParams = useSearchParams();
  const { googleAuthMutation } = useAuth();
  const calledRef = useRef(false);

  useEffect(() => {
    const code = searchParams.get("code");
    if (code && !calledRef.current) {
      calledRef.current = true;
      googleAuthMutation.mutate({ code });
    }
  }, [searchParams, googleAuthMutation]);

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <h1 className="text-center text-2xl font-bold text-gray-900">
          Signing in with Google
        </h1>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        {googleAuthMutation.error ? (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
            {googleAuthMutation.error.message || "Failed to sign in with Google. Please try again."}
          </div>
        ) : (
          <div className="flex items-center gap-2 text-gray-600">
            <svg
              className="h-5 w-5 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Please wait...</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <Card className="w-full max-w-md">
          <CardContent className="flex items-center justify-center p-8">
            <span className="text-gray-600">Loading...</span>
          </CardContent>
        </Card>
      }
    >
      <GoogleCallbackInner />
    </Suspense>
  );
}
