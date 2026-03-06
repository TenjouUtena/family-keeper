"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { ListDetailResponse } from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUpdateList } from "@/hooks/useLists";

const roleOptions = [
  { value: "", label: "Everyone" },
  { value: "parent", label: "Parents only" },
  { value: "child", label: "Children only" },
];

export function ListSettings({
  list,
  familyId,
  onClose,
}: {
  list: ListDetailResponse;
  familyId: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const updateList = useUpdateList(familyId, list.id);

  const [name, setName] = useState(list.name);
  const [visibleToRole, setVisibleToRole] = useState(
    list.visible_to_role ?? "",
  );
  const [editableByRole, setEditableByRole] = useState(
    list.editable_by_role ?? "",
  );

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    await updateList.mutateAsync({
      name: name.trim(),
      visible_to_role: visibleToRole || null,
      editable_by_role: editableByRole || null,
    });
    onClose();
  };

  const handleArchive = async () => {
    await updateList.mutateAsync({ is_archived: true });
    router.push(`/families/${familyId}/lists`);
  };

  return (
    <div className="border-t border-gray-200 bg-gray-50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">List Settings</h3>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600"
          aria-label="Close settings"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="2"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <form onSubmit={handleSave} className="space-y-3">
        <Input
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={100}
          required
        />

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
            {roleOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
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
            {roleOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {updateList.error && (
          <p className="text-sm text-red-600">{updateList.error.message}</p>
        )}

        <div className="flex items-center justify-between pt-1">
          <button
            type="button"
            onClick={handleArchive}
            className="text-sm text-red-600 hover:text-red-700"
          >
            Archive list
          </button>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              loading={updateList.isPending}
              disabled={!name.trim()}
            >
              Save
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
