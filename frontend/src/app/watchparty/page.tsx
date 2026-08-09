"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getWatchParties } from "@/lib/api";
import type { WatchParty, WatchPartyMyStatus, WatchPartyStatus } from "@/lib/types";

const STATUS_LABEL: Record<WatchPartyStatus, string> = {
  scheduled: "Planifiée",
  live: "En cours",
  ended: "Terminée",
  canceled: "Annulée",
};

const MY_STATUS_LABEL: Record<NonNullable<WatchPartyMyStatus>, string> = {
  host: "Tu organises",
  moderator: "Modérateur",
  member: "Tu participes",
  pending: "Demande envoyée",
  rejected: "Demande refusée",
};

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function WatchPartyListPage() {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [parties, setParties] = useState<WatchParty[]>([]);
  const [loading, setLoading] = useState(true);

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
        const page = await getWatchParties(token);
        if (!cancelled) setParties(page.results);
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
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Visionnage entre amis</h1>
        <Link
          href="/watchparty/create"
          className="rounded-full bg-accent px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-accent-hover"
        >
          Créer une séance
        </Link>
      </div>
      <p className="mt-2 text-muted">
        Choisis un film, fixe une heure, et regarde-le en direct avec d&apos;autres personnes que tu acceptes.
      </p>

      {parties.length === 0 ? (
        <p className="mt-6 text-muted">Aucune séance pour l&apos;instant.</p>
      ) : (
        <ul className="mt-6 divide-y divide-white/5">
          {parties.map((party) => (
            <li key={party.id}>
              <Link
                href={`/watchparty/${party.id}`}
                className="flex items-center justify-between gap-4 py-4 hover:text-accent"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-foreground">{party.display_title}</p>
                  <p className="text-sm text-muted">
                    {formatDate(party.scheduled_at)} · organisé par {party.host_email} · {party.member_count} participant
                    {party.member_count > 1 ? "s" : ""}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <span
                    className={
                      party.status === "live"
                        ? "rounded-full bg-accent px-2.5 py-0.5 text-xs font-bold uppercase text-white"
                        : "text-xs text-muted"
                    }
                  >
                    {STATUS_LABEL[party.status]}
                  </span>
                  {party.my_status && (
                    <p className="mt-1 text-xs text-muted">{MY_STATUS_LABEL[party.my_status]}</p>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
