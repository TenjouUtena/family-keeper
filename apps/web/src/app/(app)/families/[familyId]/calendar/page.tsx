"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { ConnectGoogleCal } from "@/components/connect-google-cal";
import { FamilyCalendar } from "@/components/family-calendar";
import { useFamily } from "@/hooks/useFamilies";

export default function CalendarPage() {
  const { familyId } = useParams<{ familyId: string }>();
  const { data: family, isLoading } = useFamily(familyId);

  if (isLoading || !family) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <Link
          href={`/families/${familyId}`}
          className="text-sm text-indigo-600 hover:text-indigo-700"
        >
          &larr; {family.name}
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">
          Family Calendar
        </h1>
      </div>

      <div className="mb-6">
        <ConnectGoogleCal />
      </div>

      <FamilyCalendar familyId={familyId} />
    </div>
  );
}
