"use client";

import type { NotificationResponse } from "@family-keeper/shared-types";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  useDismissNotification,
  useMarkAllRead,
  useMarkRead,
  useNotifications,
} from "@/hooks/useNotifications";

function timeAgo(dateStr: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(dateStr).getTime()) / 1000,
  );
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function notificationIcon(type: string) {
  if (type === "task_assigned") {
    return (
      <svg
        className="h-5 w-5 text-indigo-600"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth="1.5"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"
        />
      </svg>
    );
  }
  if (type === "task_completed") {
    return (
      <svg
        className="h-5 w-5 text-green-600"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth="1.5"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
        />
      </svg>
    );
  }
  // items_added / default
  return (
    <svg
      className="h-5 w-5 text-blue-600"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth="1.5"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 4.5v15m7.5-7.5h-15"
      />
    </svg>
  );
}

function NotificationCard({
  notification,
  onNavigate,
}: {
  notification: NotificationResponse;
  onNavigate: (n: NotificationResponse) => void;
}) {
  const dismiss = useDismissNotification();

  return (
    <div
      className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
        notification.is_read
          ? "border-gray-200 bg-white"
          : "border-indigo-200 bg-indigo-50"
      }`}
    >
      <button
        className="flex flex-1 items-start gap-3 text-left"
        onClick={() => onNavigate(notification)}
      >
        <div className="mt-0.5 shrink-0">
          {notificationIcon(notification.type)}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900">
            {notification.title}
          </p>
          <p className="mt-0.5 text-sm text-gray-600">{notification.body}</p>
          <p className="mt-1 text-xs text-gray-400">
            {timeAgo(notification.created_at)}
          </p>
        </div>
      </button>
      <button
        className="shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        onClick={(e) => {
          e.stopPropagation();
          dismiss.mutate(notification.id);
        }}
        title="Dismiss"
      >
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6 18 18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  );
}

export default function InboxPage() {
  const router = useRouter();
  const { data, isLoading } = useNotifications();
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();

  const handleNavigate = (notification: NotificationResponse) => {
    if (!notification.is_read) {
      markRead.mutate(notification.id);
    }
    if (notification.url) {
      router.push(notification.url);
    }
  };

  return (
    <div className="mx-auto max-w-2xl p-6 pb-24">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inbox</h1>
          {data && data.unread_count > 0 && (
            <p className="mt-1 text-sm text-gray-600">
              {data.unread_count} unread
            </p>
          )}
        </div>
        {data && data.unread_count > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => markAllRead.mutate()}
            loading={markAllRead.isPending}
          >
            Mark all read
          </Button>
        )}
      </div>

      <div className="mt-6 space-y-2">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
        ) : !data?.notifications.length ? (
          <div className="py-12 text-center">
            <svg
              className="mx-auto h-12 w-12 text-gray-300"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
              />
            </svg>
            <p className="mt-4 text-gray-500">No notifications yet</p>
            <p className="mt-1 text-sm text-gray-400">
              You&apos;ll see notifications here when tasks are assigned or
              completed.
            </p>
          </div>
        ) : (
          data.notifications.map((n) => (
            <NotificationCard
              key={n.id}
              notification={n}
              onNavigate={handleNavigate}
            />
          ))
        )}
      </div>
    </div>
  );
}
