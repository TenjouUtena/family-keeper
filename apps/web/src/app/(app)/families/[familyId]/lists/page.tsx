"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import type { ListResponse } from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useLists } from "@/hooks/useLists";

const typeLabels: Record<string, string> = {
  todo: "To-Do",
  grocery: "Grocery",
  chores: "Chores",
  custom: "Custom",
};

export default function ListsPage() {
  const { familyId } = useParams<{ familyId: string }>();
  const { data: lists, isLoading } = useLists(familyId);

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-6 pb-24">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Link
            href={`/families/${familyId}`}
            className="text-sm text-indigo-600 hover:text-indigo-700"
          >
            &larr; Family
          </Link>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">Lists</h1>
        </div>
        <Link href={`/families/${familyId}/lists/new`}>
          <Button size="sm">New List</Button>
        </Link>
      </div>

      {!lists?.length ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-lg font-medium text-gray-900">
              No lists yet
            </p>
            <p className="mt-1 text-gray-500">
              Create a grocery list, to-do list, or chore list.
            </p>
            <div className="mt-6">
              <Link href={`/families/${familyId}/lists/new`}>
                <Button>Create First List</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {lists.map((list: ListResponse) => (
            <Link
              key={list.id}
              href={`/families/${familyId}/lists/${list.id}`}
            >
              <Card className="transition-shadow hover:shadow-md">
                <CardContent className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">
                      {list.name}
                    </h2>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                        {typeLabels[list.list_type] || list.list_type}
                      </span>
                      <span className="text-sm text-gray-500">
                        {list.item_count}{" "}
                        {list.item_count === 1 ? "item" : "items"}
                      </span>
                    </div>
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
