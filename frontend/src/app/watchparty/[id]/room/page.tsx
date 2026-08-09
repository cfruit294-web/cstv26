"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getWatchParty, getWatchPartyChatHistory } from "@/lib/api";
import { WS_BASE_URL } from "@/lib/config";
import { resolveMediaUrl } from "@/lib/media";
import type { WatchParty, WatchPartyChatMessage } from "@/lib/types";
import SyncedVideoPlayer, { type RemotePlaybackEvent } from "@/components/SyncedVideoPlayer";

function formatTime(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

export default function WatchPartyRoomPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();

  const [party, setParty] = useState<WatchParty | null>(null);
  const [messages, setMessages] = useState<WatchPartyChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [connected, setConnected] = useState(false);
  const [remoteEvent, setRemoteEvent] = useState<RemotePlaybackEvent | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const nonceRef = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  const controllable = party?.my_status === "host" || party?.my_status === "moderator";
  const authorized = controllable || party?.my_status === "member";

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

      let data: WatchParty;
      try {
        data = await getWatchParty(id, token);
      } catch {
        if (!cancelled) {
          setError("Séance introuvable.");
          setLoading(false);
        }
        return;
      }
      if (cancelled) return;

      if (!(data.my_status === "host" || data.my_status === "moderator" || data.my_status === "member")) {
        setError(
          `Tu n'es pas éligible pour regarder ce film. Contacte l'organisateur de la séance (${data.host_email}) pour être accepté.`,
        );
        setLoading(false);
        return;
      }
      setParty(data);

      try {
        const chatPage = await getWatchPartyChatHistory(id, token);
        if (!cancelled) setMessages(chatPage.results);
      } catch {
        // le chat n'est qu'un complément : une erreur ici ne doit pas bloquer le lecteur
      }
      if (cancelled) return;
      setLoading(false);

      const socket = new WebSocket(`${WS_BASE_URL}/ws/watchparty/${id}/?token=${token}`);
      socketRef.current = socket;
      socket.onopen = () => setConnected(true);
      socket.onclose = () => setConnected(false);
      socket.onmessage = (event) => {
        const parsed = JSON.parse(event.data);
        if (parsed.type === "sync" || parsed.type === "playback") {
          nonceRef.current += 1;
          setRemoteEvent({ position: parsed.position, is_playing: parsed.is_playing, nonce: nonceRef.current });
        } else if (parsed.type === "chat") {
          setMessages((prev) => [
            ...prev,
            { id: parsed.id, user_email: parsed.user_email, message: parsed.content, created_at: parsed.created_at },
          ]);
        }
      };
    })();

    return () => {
      cancelled = true;
      socketRef.current?.close();
    };
  }, [authLoading, user, id, getValidAccessToken]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleLocalAction = useCallback((action: "play" | "pause" | "seek", position: number) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "playback", action, position }));
    }
  }, []);

  function handleSendChat(e: React.FormEvent) {
    e.preventDefault();
    const content = draft.trim();
    if (!content || socketRef.current?.readyState !== WebSocket.OPEN) return;
    socketRef.current.send(JSON.stringify({ type: "chat", content }));
    setDraft("");
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

  if (error || !party || !party.video || !authorized) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">{error ?? "Séance introuvable"}</h1>
        <Link href={`/watchparty/${id}`} className="mt-4 inline-block text-accent hover:underline">
          Retour à la séance
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
      <Link href={`/watchparty/${id}`} className="text-sm text-muted hover:text-accent">
        &larr; {party.display_title}
      </Link>

      <div className="mt-3 grid gap-4 lg:grid-cols-[1fr_320px]">
        <div>
          <SyncedVideoPlayer
            src={resolveMediaUrl(party.video.hls_master_playlist)!}
            poster={resolveMediaUrl(party.video.thumbnail)}
            controllable={controllable}
            onLocalAction={handleLocalAction}
            remoteEvent={remoteEvent}
          />
          {!controllable && (
            <p className="mt-2 text-xs text-muted">
              La lecture est contrôlée par l&apos;hôte ou un modérateur.
            </p>
          )}
        </div>

        <div className="flex h-[60vh] flex-col rounded-lg bg-surface ring-1 ring-white/5 lg:h-[70vh]">
          <div className="flex-1 space-y-2 overflow-y-auto p-3">
            {messages.map((message) => (
              <div key={message.id} className="text-sm">
                <span className="font-medium text-foreground">{message.user_email.split("@")[0]}</span>{" "}
                <span className="text-muted">{message.message}</span>{" "}
                <span className="text-[10px] text-muted">{formatTime(message.created_at)}</span>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={handleSendChat} className="flex gap-2 border-t border-white/10 p-3">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={connected ? "Message..." : "Connexion..."}
              disabled={!connected}
              className="flex-1 rounded-full border border-white/10 bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={!connected || !draft.trim()}
              className="rounded-full bg-accent px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
            >
              Envoyer
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
