"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useFamilies } from "@/hooks/useFamilies";

export default function FamiliesPage() {
  const { data: families, isLoading } = useFamilies();

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">My Families</h1>
        <div className="flex gap-2">
          <Link href="/families/join">
            <Button variant="secondary" size="sm">
              Join
            </Button>
          </Link>
          <Link href="/families/new">
            <Button size="sm">Create</Button>
          </Link>
        </div>
      </div>

      {!families?.length ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-lg font-medium text-gray-900">
              No families yet
            </p>
            <p className="mt-1 text-gray-500">
              Create a family or join one with an invite code.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <Link href="/families/join">
                <Button variant="secondary">Join Family</Button>
              </Link>
              <Link href="/families/new">
                <Button>Create Family</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {families.map((family) => (
            <Link key={family.id} href={`/families/${family.id}`}>
              <Card className="transition-shadow hover:shadow-md">
                <CardContent className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">
                      {family.name}
                    </h2>
                    <p className="text-sm text-gray-500">
                      {family.member_count}{" "}
                      {family.member_count === 1 ? "member" : "members"}
                    </p>
                  </div>
                  <svg
                    className="h-5 w-5 text-gray-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth="2"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M8.25 4.5l7.5 7.5-7.5 7.5"
                    />
                  </svg>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
