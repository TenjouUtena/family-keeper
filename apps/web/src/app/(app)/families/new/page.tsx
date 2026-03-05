"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCreateFamily } from "@/hooks/useFamilies";

export default function CreateFamilyPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const createFamily = useCreateFamily();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const family = await createFamily.mutateAsync(name.trim());
    router.push(`/families/${family.id}`);
  };

  return (
    <div className="mx-auto max-w-lg p-6">
      <Card>
        <CardHeader>
          <h1 className="text-xl font-bold text-gray-900">
            Create a Family
          </h1>
          <p className="text-sm text-gray-500">
            Start a new family group and invite your members.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Family Name"
              placeholder="e.g., The Smith Family"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              required
            />
            {createFamily.error && (
              <p className="text-sm text-red-600">
                {createFamily.error.message}
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
                loading={createFamily.isPending}
                disabled={!name.trim()}
              >
                Create Family
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
