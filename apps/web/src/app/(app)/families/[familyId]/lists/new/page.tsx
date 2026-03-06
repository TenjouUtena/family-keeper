"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCreateList } from "@/hooks/useLists";

const listTypes = [
  { value: "todo", label: "To-Do" },
  { value: "grocery", label: "Grocery" },
  { value: "chores", label: "Chores" },
  { value: "custom", label: "Custom" },
];

export default function NewListPage() {
  const { familyId } = useParams<{ familyId: string }>();
  const router = useRouter();
  const createList = useCreateList(familyId);

  const [name, setName] = useState("");
  const [listType, setListType] = useState("todo");
  const [requirePhoto, setRequirePhoto] = useState(false);
  const [visibleToRole, setVisibleToRole] = useState("");
  const [editableByRole, setEditableByRole] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const list = await createList.mutateAsync({
      name: name.trim(),
      list_type: listType,
      require_photo_completion: requirePhoto,
      visible_to_role: visibleToRole || null,
      editable_by_role: editableByRole || null,
    });
    router.push(`/families/${familyId}/lists/${list.id}`);
  };

  return (
    <div className="mx-auto max-w-lg p-6">
      <Card>
        <CardHeader>
          <h1 className="text-xl font-bold text-gray-900">Create a List</h1>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="List Name"
              placeholder="e.g., Weekly Groceries"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              required
            />

            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">
                List Type
              </label>
              <div className="grid grid-cols-2 gap-2">
                {listTypes.map((type) => (
                  <button
                    key={type.value}
                    type="button"
                    onClick={() => setListType(type.value)}
                    className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      listType === type.value
                        ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                        : "border-gray-300 text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            </div>

            {listType === "chores" && (
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={requirePhoto}
                  onChange={(e) => setRequirePhoto(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600"
                />
                <span className="text-sm text-gray-700">
                  Require photo proof for completion
                </span>
              </label>
            )}

            <div className="space-y-1">
              <label
                htmlFor="visible-to"
                className="block text-sm font-medium text-gray-700"
              >
                Visible to
              </label>
              <select
                id="visible-to"
                value={visibleToRole}
                onChange={(e) => setVisibleToRole(e.target.value)}
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">Everyone</option>
                <option value="parent">Parents only</option>
                <option value="child">Children only</option>
              </select>
            </div>

            <div className="space-y-1">
              <label
                htmlFor="editable-by"
                className="block text-sm font-medium text-gray-700"
              >
                Editable by
              </label>
              <select
                id="editable-by"
                value={editableByRole}
                onChange={(e) => setEditableByRole(e.target.value)}
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">Everyone</option>
                <option value="parent">Parents only</option>
                <option value="child">Children only</option>
              </select>
            </div>

            {createList.error && (
              <p className="text-sm text-red-600">
                {createList.error.message}
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
                loading={createList.isPending}
                disabled={!name.trim()}
              >
                Create List
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
