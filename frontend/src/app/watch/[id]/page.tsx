"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { ApiError, getVideo } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import type { Video } from "@/lib/types";
import VideoPlayer from "@/components/VideoPlayer";

export default function WatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [video, setVideo] = useState<Video | null>(null);
  const [error, setError] = useState<string | null>(null);
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
        const data = await getVideo(id, token);
        if (!cancelled) setVideo(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && err.status === 403
              ? "Tu n'as pas accès à cette vidéo."
              : "Vidéo introuvable.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, id, getValidAccessToken]);

  if (authLoading || loading) {
    return <p className="px-4 py-24 text-center text-muted">Chargement...</p>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Connexion requise</h1>
        <p className="mt-3 text-muted">Connecte-toi pour regarder cette vidéo.</p>
        <Link
          href="/login"
          className="mt-5 inline-block rounded-full bg-accent px-6 py-2 font-semibold text-white transition hover:bg-accent-hover"
        >
          Se connecter
        </Link>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">{error ?? "Vidéo introuvable"}</h1>
      </div>
    );
  }

  if (video.status !== "ready" || !video.hls_master_playlist) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Vidéo pas encore disponible</h1>
        <p className="mt-3 text-muted">Cette vidéo est en cours de traitement, reviens plus tard.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <VideoPlayer
        src={resolveMediaUrl(video.hls_master_playlist)!}
        poster={resolveMediaUrl(video.thumbnail)}
        subtitles={video.subtitles.map((subtitle) => ({
          language: subtitle.language,
          label: subtitle.label,
          url: resolveMediaUrl(subtitle.url)!,
        }))}
      />
      <h1 className="mt-4 text-2xl font-bold text-foreground">{video.title}</h1>
      {video.description && <p className="mt-2 text-muted">{video.description}</p>}
    </div>
  );
}
