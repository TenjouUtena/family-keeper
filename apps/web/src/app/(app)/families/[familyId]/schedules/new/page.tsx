"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCreateSchedule } from "@/hooks/useSchedules";

export default function NewSchedulePage() {
  const { familyId } = useParams<{ familyId: string }>();
  const router = useRouter();
  const createSchedule = useCreateSchedule(familyId);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [visibleToRole, setVisibleToRole] = useState("");
  const [editableByRole, setEditableByRole] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const schedule = await createSchedule.mutateAsync({
      name: name.trim(),
      description: description.trim() || null,
      visible_to_role: visibleToRole || null,
      editable_by_role: editableByRole || null,
    });
    router.push(`/families/${familyId}/schedules/${schedule.id}`);
  };

  return (
    <div className="mx-auto max-w-lg p-6">
      <Card>
        <CardHeader>
          <h1 className="text-xl font-bold text-gray-900">
            Create a Schedule
          </h1>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Schedule Name"
              placeholder="e.g., Soccer Season, Weekly Meals"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              required
            />

            <div className="space-y-1">
              <label
                htmlFor="description"
                className="block text-sm font-medium text-gray-700"
              >
                Description (optional)
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this schedule for?"
                rows={2}
                className="block w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

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

            {createSchedule.error && (
              <p className="text-sm text-red-600">
                {createSchedule.error.message}
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
                loading={createSchedule.isPending}
                disabled={!name.trim()}
              >
                Create Schedule
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
