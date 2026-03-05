"use client";

import type { FamilyMemberResponse } from "@family-keeper/shared-types";
import Link from "next/link";
import { useParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  useFamily,
  useRemoveMember,
  useUpdateMemberRole,
} from "@/hooks/useFamilies";
import { useAuthStore } from "@/stores/auth-store";

export default function MembersPage() {
  const { familyId } = useParams<{ familyId: string }>();
  const { data: family, isLoading } = useFamily(familyId);
  const removeMember = useRemoveMember(familyId);
  const updateRole = useUpdateMemberRole(familyId);
  const currentUser = useAuthStore((s) => s.user);

  if (isLoading || !family) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <Link
        href={`/families/${familyId}`}
        className="text-sm text-indigo-600 hover:text-indigo-700"
      >
        &larr; Back to {family.name}
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-gray-900">
        Manage Members
      </h1>

      <div className="mt-6 space-y-3">
        {family.members.map((member: FamilyMemberResponse) => (
          <Card key={member.id}>
            <CardContent className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-sm font-medium text-indigo-700">
                  {member.username[0].toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-gray-900">
                    {member.username}
                  </p>
                  <div className="flex gap-1.5">
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {member.role === "parent"
                        ? family.parent_role_name
                        : family.child_role_name}
                    </span>
                    {member.is_admin && (
                      <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs text-indigo-700">
                        Admin
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {member.user_id !== currentUser?.id && (
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      updateRole.mutate({
                        userId: member.user_id,
                        role:
                          member.role === "parent" ? "child" : "parent",
                      })
                    }
                  >
                    {member.role === "parent"
                      ? `Make ${family.child_role_name}`
                      : `Make ${family.parent_role_name}`}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-600 hover:bg-red-50 hover:text-red-700"
                    onClick={() => {
                      if (
                        confirm(
                          `Remove ${member.username} from ${family.name}?`,
                        )
                      ) {
                        removeMember.mutate(member.user_id);
                      }
                    }}
                  >
                    Remove
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
