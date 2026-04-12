"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { ScheduleDetailResponse } from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUpdateSchedule } from "@/hooks/useSchedules";

const roleOptions = [
  { value: "", label: "Everyone" },
  { value: "parent", label: "Parents only" },
  { value: "child", label: "Children only" },
];

export function ScheduleSettings({
  schedule,
  familyId,
  onClose,
}: {
  schedule: ScheduleDetailResponse;
  familyId: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const updateSchedule = useUpdateSchedule(familyId, schedule.id);

  const [name, setName] = useState(schedule.name);
  const [description, setDescription] = useState(schedule.description ?? "");
  const [visibleToRole, setVisibleToRole] = useState(
    schedule.visible_to_role ?? "",
  );
  const [editableByRole, setEditableByRole] = useState(
    schedule.editable_by_role ?? "",
  );

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    await updateSchedule.mutateAsync({
      name: name.trim(),
      description: description.trim() || null,
      visible_to_role: visibleToRole || null,
      editable_by_role: editableByRole || null,
    });
    onClose();
  };

  const handleArchive = async () => {
    await updateSchedule.mutateAsync({ is_archived: true });
    router.push(`/families/${familyId}/schedules`);
  };

  return (
    <div className="border-t border-gray-200 bg-gray-50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">
          Schedule Settings
        </h3>
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
            htmlFor="sched-description"
            className="block text-sm font-medium text-gray-700"
          >
            Description
          </label>
          <textarea
            id="sched-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What is this schedule for?"
            rows={2}
            className="block w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="space-y-1">
          <label
            htmlFor="sched-visible-to"
            className="block text-sm font-medium text-gray-700"
          >
            Visible to
          </label>
          <select
            id="sched-visible-to"
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
            htmlFor="sched-editable-by"
            className="block text-sm font-medium text-gray-700"
          >
            Editable by
          </label>
          <select
            id="sched-editable-by"
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

        {updateSchedule.error && (
          <p className="text-sm text-red-600">
            {updateSchedule.error.message}
          </p>
        )}

        <div className="flex items-center justify-between pt-1">
          <button
            type="button"
            onClick={handleArchive}
            className="text-sm text-red-600 hover:text-red-700"
          >
            Archive schedule
          </button>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              loading={updateSchedule.isPending}
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
