"use client";

import { resolveMediaUrl } from "@/lib/media";
import type { LiveStream } from "@/lib/types";
import VideoPlayer from "@/components/VideoPlayer";

function formatSchedule(iso: string | null) {
  if (!iso) return null;
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function LiveHero({ stream }: { stream: LiveStream | null }) {
  const isLive = stream?.status === "live";
  const isScheduled = stream?.status === "scheduled";
  const hasReplay = stream?.status === "ended" && stream.replay?.status === "ready" && Boolean(stream.replay.hls_master_playlist);
  const isUnavailable = !isLive && !isScheduled && !hasReplay;

  return (
    <section className="relative overflow-hidden rounded-2xl bg-surface">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "radial-gradient(circle at 50% 30%, rgba(224,41,58,0.18), transparent 60%)",
        }}
      />
      <div className="relative grid gap-6 p-4 sm:p-8 lg:grid-cols-[2fr_1fr] lg:items-center">
        <div className="overflow-hidden rounded-xl border-2 border-amber-400/70">
          {isLive && stream && <VideoPlayer src={stream.hls_playback_url} />}

          {isScheduled && stream && (
            <div className="flex aspect-video flex-col items-center justify-center gap-3 bg-black text-center">
              <span className="rounded-full bg-surface-2 px-3 py-1 text-xs font-bold uppercase tracking-wide text-muted">
                Prochain live
              </span>
              <p className="text-lg font-semibold text-foreground">{stream.title}</p>
              {stream.scheduled_at && (
                <p className="text-sm text-muted">{formatSchedule(stream.scheduled_at)}</p>
              )}
            </div>
          )}

          {hasReplay && stream?.replay && (
            <VideoPlayer
              src={resolveMediaUrl(stream.replay.hls_master_playlist)!}
              poster={resolveMediaUrl(stream.replay.thumbnail)}
            />
          )}

          {isUnavailable && (
            <div className="flex aspect-video items-center justify-center bg-black text-center">
              <p className="px-6 text-muted">Le direct est momentanément indisponible.</p>
            </div>
          )}
        </div>

        <div>
          <span className="inline-flex items-center gap-2 rounded-md bg-accent px-2 py-1 text-xs font-bold uppercase tracking-wide text-white">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" />
            Live
          </span>
          <h1 className="mt-3 text-2xl font-bold leading-snug text-foreground sm:text-3xl">
            {stream?.status === "live"
              ? <>Vous suivez actuellement<br />{stream.title} en Live !</>
              : "Aucun direct en cours pour le moment"}
          </h1>
          {stream?.description && <p className="mt-3 text-sm text-muted">{stream.description}</p>}
        </div>
      </div>
    </section>
  );
}
