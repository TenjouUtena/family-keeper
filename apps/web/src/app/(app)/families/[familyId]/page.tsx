"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import type { FamilyMemberResponse } from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useCreateInvite, useFamily } from "@/hooks/useFamilies";

export default function FamilyHomePage() {
  const { familyId } = useParams<{ familyId: string }>();
  const { data: family, isLoading } = useFamily(familyId);
  const createInvite = useCreateInvite(familyId);
  const [inviteCode, setInviteCode] = useState<string | null>(null);

  if (isLoading || !family) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  const currentUserIsAdmin = family.members.some(
    (m: FamilyMemberResponse) => m.is_admin,
  );

  const handleCreateInvite = async () => {
    const invite = await createInvite.mutateAsync({});
    setInviteCode(invite.code);
  };

  const handleShare = async () => {
    if (!inviteCode) return;
    if (navigator.share) {
      await navigator.share({
        title: `Join ${family.name}`,
        text: `Use this code to join ${family.name}: ${inviteCode}`,
      });
    } else {
      await navigator.clipboard.writeText(inviteCode);
    }
  };

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="mb-6">
        <Link
          href="/families"
          className="text-sm text-indigo-600 hover:text-indigo-700"
        >
          &larr; All Families
        </Link>
        <div className="mt-2 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">{family.name}</h1>
          {currentUserIsAdmin && (
            <Link href={`/families/${familyId}/settings`}>
              <Button variant="ghost" size="sm">
                Settings
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mb-6 space-y-3">
        <Link href={`/families/${familyId}/lists`}>
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100">
                  <svg className="h-5 w-5 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
                  </svg>
                </div>
                <div>
                  <h2 className="font-semibold text-gray-900">Lists</h2>
                  <p className="text-sm text-gray-500">Grocery, to-do, chores</p>
                </div>
              </div>
              <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </CardContent>
          </Card>
        </Link>

        <Link href={`/families/${familyId}/calendar`}>
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
                  <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                  </svg>
                </div>
                <div>
                  <h2 className="font-semibold text-gray-900">Calendar</h2>
                  <p className="text-sm text-gray-500">Unified family schedule</p>
                </div>
              </div>
              <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Members */}
      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Members ({family.member_count})
          </h2>
          {currentUserIsAdmin && (
            <Link href={`/families/${familyId}/members`}>
              <Button variant="ghost" size="sm">
                Manage
              </Button>
            </Link>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          {family.members.map((member: FamilyMemberResponse) => (
            <div
              key={member.id}
              className="flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-sm font-medium text-indigo-700">
                  {member.username[0].toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-gray-900">
                    {member.username}
                  </p>
                  <p className="text-sm text-gray-500">{member.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                  {member.role === "parent"
                    ? family.parent_role_name
                    : family.child_role_name}
                </span>
                {member.is_admin && (
                  <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
                    Admin
                  </span>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Invite */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">
            Invite Members
          </h2>
        </CardHeader>
        <CardContent>
          {inviteCode ? (
            <div className="space-y-3">
              <div className="rounded-lg bg-gray-50 p-4 text-center">
                <p className="text-sm text-gray-500">Invite Code</p>
                <p className="mt-1 font-mono text-2xl font-bold tracking-widest text-indigo-600">
                  {inviteCode}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={handleShare}
                  className="flex-1"
                >
                  {"share" in navigator ? "Share" : "Copy Code"}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setInviteCode(null)}
                >
                  Done
                </Button>
              </div>
            </div>
          ) : (
            <Button
              onClick={handleCreateInvite}
              loading={createInvite.isPending}
              className="w-full"
            >
              Generate Invite Code
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
