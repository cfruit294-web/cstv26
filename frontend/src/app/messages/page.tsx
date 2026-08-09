"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getConversations } from "@/lib/api";
import type { Conversation } from "@/lib/types";
import NewConversationSearch from "@/components/NewConversationSearch";

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(
    new Date(iso),
  );
}

export default function MessagesPage() {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      queueMicrotask(() => setLoading(false));
      return;
    }
    let cancelled = false;
    (async () => {
      const token = await getValidAccessToken();
      if (!token || cancelled) return;
      try {
        const page = await getConversations(token);
        if (!cancelled) setConversations(page.results);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, getValidAccessToken]);

  if (authLoading || loading) {
    return <p className="px-4 py-24 text-center text-muted">Chargement...</p>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Connexion requise</h1>
        <Link href="/login" className="mt-4 inline-block text-accent hover:underline">
          Se connecter
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Messages</h1>
        {!showSearch && (
          <button
            type="button"
            onClick={() => setShowSearch(true)}
            className="rounded-full bg-accent px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-accent-hover"
          >
            Nouveau message
          </button>
        )}
      </div>

      {showSearch && (
        <div className="mt-4">
          <NewConversationSearch onClose={() => setShowSearch(false)} />
        </div>
      )}

      {conversations.length === 0 ? (
        <p className="mt-6 text-muted">Aucune conversation pour l&apos;instant.</p>
      ) : (
        <ul className="mt-6 divide-y divide-white/5">
          {conversations.map((conversation) => {
            const others = conversation.participant_emails.filter((email) => email !== user.email);
            return (
              <li key={conversation.id}>
                <Link
                  href={`/messages/${conversation.id}`}
                  className="flex items-center justify-between gap-4 py-4 hover:text-accent"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">{others.join(", ") || "Toi"}</p>
                    <p className="truncate text-sm text-muted">
                      {conversation.last_message ? conversation.last_message.content : "Aucun message"}
                    </p>
                  </div>
                  <span className="shrink-0 text-xs text-muted">{formatDate(conversation.updated_at)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
