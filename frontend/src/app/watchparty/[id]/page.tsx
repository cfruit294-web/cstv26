"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  acceptWatchPartyMember,
  cancelWatchParty,
  endWatchParty,
  formatApiError,
  getWatchParty,
  getWatchPartyMembers,
  joinWatchParty,
  promoteWatchPartyMember,
  rejectWatchPartyMember,
  startWatchParty,
} from "@/lib/api";
import type { WatchParty, WatchPartyMembership } from "@/lib/types";

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function WatchPartyLobbyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const router = useRouter();

  const [party, setParty] = useState<WatchParty | null>(null);
  const [members, setMembers] = useState<WatchPartyMembership[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canModerate = party?.my_status === "host" || party?.my_status === "moderator";
  const isHost = party?.my_status === "host";

  const load = useCallback(async () => {
    const token = await getValidAccessToken();
    if (!token) return;
    try {
      const data = await getWatchParty(id, token);
      setParty(data);
      if (data.my_status === "host" || data.my_status === "moderator") {
        const page = await getWatchPartyMembers(id, token);
        setMembers(page.results);
      }
    } catch {
      setError("Séance introuvable.");
    } finally {
      setLoading(false);
    }
  }, [id, getValidAccessToken]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      queueMicrotask(() => setLoading(false));
      return;
    }
    queueMicrotask(() => {
      load();
    });
  }, [authLoading, user, load]);

  async function handleJoin() {
    setBusy(true);
    setError(null);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      await joinWatchParty(id, token);
      await load();
    } catch (err) {
      setError(formatApiError(err, "Impossible d'envoyer la demande."));
    } finally {
      setBusy(false);
    }
  }

  async function handleDecision(memberId: string, decision: "accept" | "reject") {
    const token = await getValidAccessToken();
    if (!token) return;
    const action = decision === "accept" ? acceptWatchPartyMember : rejectWatchPartyMember;
    await action(id, memberId, token);
    await load();
  }

  async function handlePromote(memberId: string) {
    const token = await getValidAccessToken();
    if (!token) return;
    await promoteWatchPartyMember(id, memberId, token);
    await load();
  }

  async function handleStart() {
    setBusy(true);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      await startWatchParty(id, token);
      router.push(`/watchparty/${id}/room`);
    } finally {
      setBusy(false);
    }
  }

  async function handleEnd() {
    const token = await getValidAccessToken();
    if (!token) return;
    await endWatchParty(id, token);
    await load();
  }

  async function handleCancel() {
    const token = await getValidAccessToken();
    if (!token) return;
    await cancelWatchParty(id, token);
    await load();
  }

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

  if (error || !party) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">{error ?? "Séance introuvable"}</h1>
        <Link href="/watchparty" className="mt-4 inline-block text-accent hover:underline">
          Retour
        </Link>
      </div>
    );
  }

  const pending = members.filter((m) => m.status === "pending");
  const accepted = members.filter((m) => m.status === "accepted");

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <Link href="/watchparty" className="text-sm text-muted hover:text-accent">
        &larr; Visionnage entre amis
      </Link>

      <h1 className="mt-2 text-2xl font-bold text-foreground">{party.display_title}</h1>
      <p className="mt-1 text-muted">
        {formatDate(party.scheduled_at)} · organisé par {party.host_email}
      </p>
      <p className="mt-1 text-sm text-muted">
        {party.member_count} participant{party.member_count > 1 ? "s" : ""}
      </p>

      {error && <p className="mt-4 text-sm text-accent">{error}</p>}

      <div className="mt-6 flex flex-wrap gap-3">
        {party.my_status === null && party.status === "scheduled" && (
          <button
            type="button"
            onClick={handleJoin}
            disabled={busy}
            className="rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
          >
            Demander à rejoindre
          </button>
        )}
        {party.my_status === "pending" && (
          <p className="text-muted">Demande envoyée, en attente d&apos;acceptation.</p>
        )}
        {party.my_status === "rejected" && (
          <div>
            <p className="text-muted">
              Tu n&apos;es pas éligible pour regarder ce film. Contacte l&apos;organisateur de la séance (
              {party.host_email}) pour être accepté.
            </p>
            <button type="button" onClick={handleJoin} disabled={busy} className="mt-2 text-sm text-accent hover:underline">
              Redemander
            </button>
          </div>
        )}
        {(party.my_status === "host" || party.my_status === "moderator" || party.my_status === "member") && (
          <>
            {party.status === "live" && (
              <Link
                href={`/watchparty/${id}/room`}
                className="rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover"
              >
                Rejoindre la séance
              </Link>
            )}
            {party.status === "scheduled" && canModerate && (
              <button
                type="button"
                onClick={handleStart}
                disabled={busy}
                className="rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
              >
                Démarrer la séance
              </button>
            )}
            {party.status === "scheduled" && !canModerate && (
              <p className="text-muted">En attente du démarrage par l&apos;hôte.</p>
            )}
            {party.status === "live" && canModerate && (
              <button
                type="button"
                onClick={handleEnd}
                className="rounded-full border border-white/10 px-6 py-2.5 text-foreground transition hover:border-accent hover:text-accent"
              >
                Terminer
              </button>
            )}
            {party.status === "scheduled" && isHost && (
              <button
                type="button"
                onClick={handleCancel}
                className="rounded-full border border-white/10 px-6 py-2.5 text-foreground transition hover:border-accent hover:text-accent"
              >
                Annuler la séance
              </button>
            )}
          </>
        )}
      </div>

      {canModerate && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-foreground">Demandes en attente</h2>
          {pending.length === 0 ? (
            <p className="mt-2 text-sm text-muted">Aucune demande en attente.</p>
          ) : (
            <ul className="mt-3 divide-y divide-white/5">
              {pending.map((member) => (
                <li key={member.id} className="flex items-center justify-between gap-3 py-2">
                  <span className="text-sm text-foreground">{member.user_email}</span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleDecision(member.id, "accept")}
                      className="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-white hover:bg-accent-hover"
                    >
                      Accepter
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDecision(member.id, "reject")}
                      className="rounded-full border border-white/10 px-3 py-1 text-xs text-foreground hover:border-accent hover:text-accent"
                    >
                      Refuser
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <h2 className="mt-6 text-lg font-semibold text-foreground">Participants acceptés</h2>
          {accepted.length === 0 ? (
            <p className="mt-2 text-sm text-muted">Personne pour l&apos;instant.</p>
          ) : (
            <ul className="mt-3 divide-y divide-white/5">
              {accepted.map((member) => (
                <li key={member.id} className="flex items-center justify-between gap-3 py-2">
                  <span className="text-sm text-foreground">
                    {member.user_email} {member.role === "moderator" && <span className="text-muted">(modérateur)</span>}
                  </span>
                  {isHost && member.role !== "moderator" && (
                    <button
                      type="button"
                      onClick={() => handlePromote(member.id)}
                      className="text-xs text-muted hover:text-accent"
                    >
                      Nommer modérateur
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
