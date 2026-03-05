"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useFamily, useUpdateFamily } from "@/hooks/useFamilies";

export default function FamilySettingsPage() {
  const { familyId } = useParams<{ familyId: string }>();
  const { data: family, isLoading } = useFamily(familyId);
  const updateFamily = useUpdateFamily(familyId);

  const [name, setName] = useState("");
  const [parentRole, setParentRole] = useState("");
  const [childRole, setChildRole] = useState("");

  useEffect(() => {
    if (family) {
      setName(family.name);
      setParentRole(family.parent_role_name);
      setChildRole(family.child_role_name);
    }
  }, [family]);

  if (isLoading || !family) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  const hasChanges =
    name !== family.name ||
    parentRole !== family.parent_role_name ||
    childRole !== family.child_role_name;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await updateFamily.mutateAsync({
      name: name !== family.name ? name : undefined,
      parent_role_name:
        parentRole !== family.parent_role_name ? parentRole : undefined,
      child_role_name:
        childRole !== family.child_role_name ? childRole : undefined,
    });
  };

  return (
    <div className="mx-auto max-w-lg p-6">
      <Link
        href={`/families/${familyId}`}
        className="text-sm text-indigo-600 hover:text-indigo-700"
      >
        &larr; Back to {family.name}
      </Link>

      <Card className="mt-4">
        <CardHeader>
          <h1 className="text-xl font-bold text-gray-900">
            Family Settings
          </h1>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <Input
              label="Family Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              required
            />
            <Input
              label="Parent Role Name"
              value={parentRole}
              onChange={(e) => setParentRole(e.target.value)}
              placeholder="e.g., Parent, Mom/Dad, Guardian"
              maxLength={50}
              required
            />
            <Input
              label="Child Role Name"
              value={childRole}
              onChange={(e) => setChildRole(e.target.value)}
              placeholder="e.g., Child, Kid, Teen"
              maxLength={50}
              required
            />
            {updateFamily.error && (
              <p className="text-sm text-red-600">
                {updateFamily.error.message}
              </p>
            )}
            {updateFamily.isSuccess && (
              <p className="text-sm text-green-600">Settings saved!</p>
            )}
            <Button
              type="submit"
              loading={updateFamily.isPending}
              disabled={!hasChanges}
            >
              Save Changes
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
