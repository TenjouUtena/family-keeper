"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useJoinFamily } from "@/hooks/useFamilies";

const QRScanner = dynamic(
  () => import("@/components/qr-scanner").then((m) => ({ default: m.QRScanner })),
  { ssr: false },
);

function JoinFamilyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [code, setCode] = useState("");
  const [showScanner, setShowScanner] = useState(false);
  const joinFamily = useJoinFamily();

  useEffect(() => {
    const codeParam = searchParams.get("code");
    if (codeParam && codeParam.length === 8) {
      setCode(codeParam.toUpperCase());
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length !== 8) return;

    const family = await joinFamily.mutateAsync(code.toUpperCase());
    router.push(`/families/${family.id}`);
  };

  const handleQRScan = (decodedText: string) => {
    setShowScanner(false);
    try {
      const url = new URL(decodedText);
      const scannedCode = url.searchParams.get("code");
      if (scannedCode && scannedCode.length === 8) {
        setCode(scannedCode.toUpperCase());
        return;
      }
    } catch {
      // Not a URL — try treating raw text as a code
    }
    if (decodedText.length === 8 && /^[A-Z0-9]+$/i.test(decodedText)) {
      setCode(decodedText.toUpperCase());
    }
  };

  return (
    <div className="mx-auto max-w-lg p-6">
      <Card>
        <CardHeader>
          <h1 className="text-xl font-bold text-gray-900">
            Join a Family
          </h1>
          <p className="text-sm text-gray-500">
            Enter the 8-character invite code or scan a QR code.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Invite Code"
              placeholder="e.g., AB3CD5EF"
              value={code}
              onChange={(e) =>
                setCode(e.target.value.toUpperCase().slice(0, 8))
              }
              maxLength={8}
              className="text-center text-lg font-mono tracking-widest"
              required
            />

            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-gray-200" />
              <span className="text-xs text-gray-400">or</span>
              <div className="h-px flex-1 bg-gray-200" />
            </div>

            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowScanner(true)}
              className="w-full"
            >
              <svg className="mr-1.5 h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0Z" />
              </svg>
              Scan QR Code
            </Button>

            {joinFamily.error && (
              <p className="text-sm text-red-600">
                {joinFamily.error.message}
              </p>
            )}
            <div className="flex gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => router.back()}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                loading={joinFamily.isPending}
                disabled={code.length !== 8}
              >
                Join Family
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {showScanner && (
        <QRScanner
          onScan={handleQRScan}
          onClose={() => setShowScanner(false)}
        />
      )}
    </div>
  );
}

export default function JoinFamilyPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[50vh] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      }
    >
      <JoinFamilyContent />
    </Suspense>
  );
}
