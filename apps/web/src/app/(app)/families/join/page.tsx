"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useJoinFamily } from "@/hooks/useFamilies";

export default function JoinFamilyPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const joinFamily = useJoinFamily();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length !== 8) return;

    const family = await joinFamily.mutateAsync(code.toUpperCase());
    router.push(`/families/${family.id}`);
  };

  return (
    <div className="mx-auto max-w-lg p-6">
      <Card>
        <CardHeader>
          <h1 className="text-xl font-bold text-gray-900">
            Join a Family
          </h1>
          <p className="text-sm text-gray-500">
            Enter the 8-character invite code shared with you.
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
    </div>
  );
}
