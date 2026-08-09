"use client";

import Link from "next/link";
import { useNotifications } from "@/context/NotificationContext";
import Dropdown from "@/components/Dropdown";
import type { AppNotification } from "@/lib/types";

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(
    new Date(iso),
  );
}

function NotificationRow({ notification, onRead }: { notification: AppNotification; onRead: (id: string) => void }) {
  const content = (
    <div className={`px-4 py-2.5 ${notification.is_read ? "" : "bg-surface-2/60"}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{notification.title}</p>
        {!notification.is_read && <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-accent" />}
      </div>
      {notification.body && <p className="mt-0.5 truncate text-xs text-muted">{notification.body}</p>}
      <p className="mt-1 text-[10px] text-muted">{formatDate(notification.created_at)}</p>
    </div>
  );

  if (notification.link) {
    return (
      <Link href={notification.link} onClick={() => onRead(notification.id)} className="block hover:bg-surface-2">
        {content}
      </Link>
    );
  }

  return (
    <button type="button" onClick={() => onRead(notification.id)} className="block w-full text-left hover:bg-surface-2">
      {content}
    </button>
  );
}

export default function NotificationBell() {
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();

  return (
    <Dropdown
      align="right"
      showChevron={false}
      triggerClassName="relative rounded-full p-2 text-foreground transition hover:text-accent"
      panelClassName="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-lg border border-white/10 bg-surface shadow-lg"
      trigger={
        <span className="relative inline-flex">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
            <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          {unreadCount > 0 && (
            <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-bold text-white">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </span>
      }
    >
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
        <p className="text-sm font-medium text-foreground">Notifications</p>
        {unreadCount > 0 && (
          <button type="button" onClick={markAllRead} className="text-xs text-muted hover:text-accent">
            Tout marquer comme lu
          </button>
        )}
      </div>

      <div className="max-h-96 overflow-y-auto">
        {notifications.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-muted">Aucune notification.</p>
        ) : (
          <div className="divide-y divide-white/5">
            {notifications.map((notification) => (
              <NotificationRow key={notification.id} notification={notification} onRead={markRead} />
            ))}
          </div>
        )}
      </div>
    </Dropdown>
  );
}
