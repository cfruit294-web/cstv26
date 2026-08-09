"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  getNotifications,
  getUnreadNotificationCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/lib/api";
import { WS_BASE_URL } from "@/lib/config";
import type { AppNotification } from "@/lib/types";

interface NotificationContextValue {
  notifications: AppNotification[];
  unreadCount: number;
  markRead: (id: string) => void;
  markAllRead: () => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      queueMicrotask(() => {
        setNotifications([]);
        setUnreadCount(0);
      });
      return;
    }

    let cancelled = false;

    (async () => {
      const token = await getValidAccessToken();
      if (!token || cancelled) return;

      try {
        const [list, count] = await Promise.all([getNotifications(token), getUnreadNotificationCount(token)]);
        if (cancelled) return;
        setNotifications(list.results);
        setUnreadCount(count.unread_count);
      } catch {
        // La cloche reste vide si l'API est indisponible : pas bloquant pour le reste du site.
      }
      if (cancelled) return;

      const socket = new WebSocket(`${WS_BASE_URL}/ws/notifications/?token=${token}`);
      socketRef.current = socket;
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const notification: AppNotification = {
          id: data.id,
          category: data.category,
          title: data.title,
          body: data.body,
          link: data.link,
          is_read: false,
          read_at: null,
          created_at: data.created_at,
        };
        setNotifications((prev) => [notification, ...prev]);
        setUnreadCount((count) => count + 1);
      };
    })();

    return () => {
      cancelled = true;
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [authLoading, user, getValidAccessToken]);

  const markRead = useCallback(
    async (id: string) => {
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      const token = await getValidAccessToken();
      if (!token) return;
      try {
        await markNotificationRead(id, token);
        const count = await getUnreadNotificationCount(token);
        setUnreadCount(count.unread_count);
      } catch {
        // best effort : l'état local optimiste reste affiché même si la confirmation échoue
      }
    },
    [getValidAccessToken],
  );

  const markAllRead = useCallback(async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
    const token = await getValidAccessToken();
    if (!token) return;
    try {
      await markAllNotificationsRead(token);
    } catch {
      // best effort
    }
  }, [getValidAccessToken]);

  const value = useMemo(
    () => ({ notifications, unreadCount, markRead, markAllRead }),
    [notifications, unreadCount, markRead, markAllRead],
  );

  return <NotificationContext value={value}>{children}</NotificationContext>;
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotifications must be used within NotificationProvider");
  return ctx;
}
