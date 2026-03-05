"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";
import { useFamilies } from "@/hooks/useFamilies";
import { useAuthStore } from "@/stores/auth-store";

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { logoutMutation } = useAuth();
  const { data: families, isLoading } = useFamilies();

  return (
    <div className="mx-auto max-w-4xl p-6 pb-24">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome, {user?.username}
          </h1>
          <p className="mt-1 text-gray-600">Your family dashboard</p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => logoutMutation.mutate()}
          loading={logoutMutation.isPending}
        >
          Sign out
        </Button>
      </div>

      <div className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">My Families</h2>
          <Link href="/families">
            <Button variant="ghost" size="sm">
              View All
            </Button>
          </Link>
        </div>

        {isLoading ? (
          <div className="mt-4 flex justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
        ) : !families?.length ? (
          <Card className="mt-4">
            <CardContent className="py-8 text-center">
              <p className="text-gray-500">
                You haven&apos;t joined any families yet.
              </p>
              <div className="mt-4 flex justify-center gap-3">
                <Link href="/families/join">
                  <Button variant="secondary" size="sm">
                    Join Family
                  </Button>
                </Link>
                <Link href="/families/new">
                  <Button size="sm">Create Family</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {families.map((family) => (
              <Link key={family.id} href={`/families/${family.id}`}>
                <Card className="h-full transition-shadow hover:shadow-md">
                  <CardContent>
                    <h3 className="font-semibold text-gray-900">
                      {family.name}
                    </h3>
                    <p className="mt-1 text-sm text-gray-500">
                      {family.member_count}{" "}
                      {family.member_count === 1 ? "member" : "members"}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
