"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { ApiError, getLiveStream } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import type { LiveStream } from "@/lib/types";
import VideoPlayer from "@/components/VideoPlayer";

function formatDate(iso: string | null) {
  if (!iso) return null;
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function LiveWatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { isLoading: authLoading, getValidAccessToken } = useAuth();
  const [stream, setStream] = useState<LiveStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;
    (async () => {
      const token = await getValidAccessToken();
      try {
        const data = await getLiveStream(id, token ?? undefined);
        if (!cancelled) setStream(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && (err.status === 401 || err.status === 403)
              ? "Tu n'as pas accès à ce live."
              : "Live introuvable.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, id, getValidAccessToken]);

  if (authLoading || loading) {
    return <p className="px-4 py-24 text-center text-muted">Chargement...</p>;
  }

  if (error || !stream) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">{error ?? "Live introuvable"}</h1>
        <Link href="/programme" className="mt-4 inline-block text-accent hover:underline">
          Voir le programme
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      {stream.status === "live" && <VideoPlayer src={stream.hls_playback_url} />}

      {stream.status === "scheduled" && (
        <div className="flex aspect-video items-center justify-center rounded-lg bg-surface text-center">
          <div>
            <p className="text-lg font-semibold text-foreground">Diffusion à venir</p>
            {stream.scheduled_at && <p className="mt-2 text-muted">{formatDate(stream.scheduled_at)}</p>}
          </div>
        </div>
      )}

      {stream.status === "ended" && stream.replay?.status === "ready" && stream.replay.hls_master_playlist && (
        <VideoPlayer
          src={resolveMediaUrl(stream.replay.hls_master_playlist)!}
          poster={resolveMediaUrl(stream.replay.thumbnail)}
        />
      )}

      {stream.status === "ended" && (!stream.replay || stream.replay.status !== "ready") && (
        <div className="flex aspect-video items-center justify-center rounded-lg bg-surface text-center">
          <p className="text-muted">
            {stream.replay ? "Rediffusion en cours de préparation, reviens plus tard." : "Ce live est terminé, aucune rediffusion disponible."}
          </p>
        </div>
      )}

      {stream.status === "canceled" && (
        <div className="flex aspect-video items-center justify-center rounded-lg bg-surface text-center">
          <p className="text-muted">Ce live a été annulé.</p>
        </div>
      )}

      <h1 className="mt-4 text-2xl font-bold text-foreground">{stream.title}</h1>
      {stream.description && <p className="mt-2 text-muted">{stream.description}</p>}
    </div>
  );
}
