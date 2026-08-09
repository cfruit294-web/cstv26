"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getVideosByMovie } from "@/lib/api";
import type { Video } from "@/lib/types";

export default function MovieVideosSection({ movieId }: { movieId: string }) {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [videos, setVideos] = useState<Video[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (authLoading || !user) return;
    let cancelled = false;
    queueMicrotask(() => setLoading(true));
    (async () => {
      const token = await getValidAccessToken();
      if (!token || cancelled) return;
      try {
        const page = await getVideosByMovie(movieId, token);
        if (!cancelled) setVideos(page.results);
      } catch {
        if (!cancelled) setVideos([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, movieId, getValidAccessToken]);

  if (authLoading) return null;

  if (!user) {
    return (
      <div className="rounded-lg border border-white/10 bg-surface p-6 text-center">
        <p className="text-foreground">Connecte-toi pour regarder ce contenu.</p>
        <Link
          href="/login"
          className="mt-3 inline-block rounded-full bg-accent px-6 py-2 font-semibold text-white transition hover:bg-accent-hover"
        >
          Se connecter
        </Link>
      </div>
    );
  }

  if (loading || videos === null) {
    return <p className="text-muted">Chargement des vidéos...</p>;
  }

  if (videos.length === 0) {
    return <p className="text-muted">Aucune vidéo n&apos;est encore disponible pour ce titre.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      {videos.map((video) => (
        <div
          key={video.id}
          className="flex items-center justify-between rounded-lg border border-white/10 bg-surface px-4 py-3"
        >
          <div>
            <p className="font-medium text-foreground">{video.title}</p>
            <p className="text-xs text-muted">
              {video.status === "ready"
                ? "Disponible"
                : video.status === "processing"
                  ? "En traitement..."
                  : video.status === "failed"
                    ? "Échec du traitement"
                    : "En attente"}
            </p>
          </div>
          {video.status === "ready" ? (
            <Link
              href={`/watch/${video.id}`}
              className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-white transition hover:bg-accent-hover"
            >
              Regarder
            </Link>
          ) : null}
        </div>
      ))}
    </div>
  );
}
