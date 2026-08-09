"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { createWatchParty, formatApiError, getMovies, getVideosByMovie, getWatchPartySuggestions } from "@/lib/api";
import type { Movie, Video } from "@/lib/types";

function hasPoster(url: string) {
  return Boolean(url) && url !== "N/A";
}

export default function CreateWatchPartyPage() {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const router = useRouter();

  const [suggestions, setSuggestions] = useState<Movie[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Movie[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);

  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [loadingVideos, setLoadingVideos] = useState(false);

  const [title, setTitle] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (authLoading || !user) {
      queueMicrotask(() => setLoadingSuggestions(false));
      return;
    }
    let cancelled = false;
    (async () => {
      const token = await getValidAccessToken();
      if (!token || cancelled) return;
      try {
        const movies = await getWatchPartySuggestions(token);
        if (!cancelled) setSuggestions(movies);
      } finally {
        if (!cancelled) setLoadingSuggestions(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, getValidAccessToken]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    try {
      const page = await getMovies({ q });
      setResults(page.results);
      setSearched(true);
    } finally {
      setSearching(false);
    }
  }

  async function handleSelectMovie(movie: Movie) {
    setSelectedMovie(movie);
    setSelectedVideoId(null);
    setVideos([]);
    setLoadingVideos(true);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      const page = await getVideosByMovie(movie.id, token);
      const eligible = page.results.filter((v) => v.status === "ready" && v.visibility === "public");
      setVideos(eligible);
      if (eligible.length === 1) setSelectedVideoId(eligible[0].id);
    } finally {
      setLoadingVideos(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedVideoId || !scheduledAt) return;
    setError(null);
    setSubmitting(true);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      const party = await createWatchParty(
        { video: selectedVideoId, title: title.trim(), scheduled_at: new Date(scheduledAt).toISOString() },
        token,
      );
      router.push(`/watchparty/${party.id}`);
    } catch (err) {
      setError(formatApiError(err, "Impossible de créer la séance."));
      setSubmitting(false);
    }
  }

  if (authLoading) {
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
    <div className="mx-auto max-w-lg px-4 py-8 sm:px-6">
      <Link href="/watchparty" className="text-sm text-muted hover:text-accent">
        &larr; Visionnage entre amis
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-foreground">Créer une séance</h1>

      {!selectedMovie ? (
        <>
          {!loadingSuggestions && suggestions.length > 0 && (
            <div className="mt-6">
              <p className="text-sm font-medium text-foreground">Suggestions pour toi</p>
              <div className="no-scrollbar mt-2 flex gap-3 overflow-x-auto pb-2">
                {suggestions.map((movie) => (
                  <button
                    key={movie.id}
                    type="button"
                    onClick={() => handleSelectMovie(movie)}
                    className="group w-24 shrink-0 text-left"
                  >
                    <div className="relative aspect-2/3 overflow-hidden rounded-lg bg-surface ring-1 ring-white/5 transition group-hover:ring-accent">
                      {hasPoster(movie.poster_url) ? (
                        <Image
                          src={movie.poster_url}
                          alt={movie.title}
                          fill
                          sizes="96px"
                          className="object-cover transition duration-300 group-hover:scale-105"
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center px-2 text-center text-xs text-muted">
                          {movie.title}
                        </div>
                      )}
                    </div>
                    <p className="mt-1 truncate text-xs text-foreground group-hover:text-accent">{movie.title}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          <form onSubmit={handleSearch} className="mt-6 flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Chercher un film ou une série..."
              className="flex-1 rounded-full border border-white/10 bg-surface px-4 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
            <button
              type="submit"
              disabled={searching || !query.trim()}
              className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
            >
              Chercher
            </button>
          </form>

          {searched && results.length === 0 && !searching && (
            <p className="mt-4 text-sm text-muted">Aucun résultat.</p>
          )}

          <ul className="mt-4 divide-y divide-white/5">
            {results.map((movie) => (
              <li key={movie.id}>
                <button
                  type="button"
                  onClick={() => handleSelectMovie(movie)}
                  className="flex w-full items-center justify-between gap-3 py-3 text-left hover:text-accent"
                >
                  <span className="truncate text-foreground">
                    {movie.title} <span className="text-muted">({movie.year})</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <div className="rounded-lg bg-surface p-3 ring-1 ring-white/5">
            <div className="flex items-center justify-between">
              <p className="font-medium text-foreground">{selectedMovie.title}</p>
              <button
                type="button"
                onClick={() => setSelectedMovie(null)}
                className="text-sm text-muted hover:text-accent"
              >
                Changer
              </button>
            </div>
          </div>

          {loadingVideos ? (
            <p className="text-sm text-muted">Recherche d&apos;une vidéo disponible...</p>
          ) : videos.length === 0 ? (
            <p className="text-sm text-accent">
              Aucune vidéo publique et prête n&apos;est disponible pour ce titre. Une vidéo doit d&apos;abord être
              mise en ligne et rendue publique.
            </p>
          ) : (
            <div>
              <label className="text-sm font-medium text-foreground">Vidéo</label>
              <div className="mt-2 space-y-2">
                {videos.map((video) => (
                  <label key={video.id} className="flex items-center gap-2 text-sm text-foreground">
                    <input
                      type="radio"
                      name="video"
                      checked={selectedVideoId === video.id}
                      onChange={() => setSelectedVideoId(video.id)}
                    />
                    {video.title}
                  </label>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-foreground">Titre de la séance (optionnel)</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={selectedMovie.title}
              className="mt-2 w-full rounded-lg border border-white/10 bg-surface px-4 py-2.5 text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-foreground">Date et heure</label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              required
              className="mt-2 w-full rounded-lg border border-white/10 bg-surface px-4 py-2.5 text-foreground focus:border-accent focus:outline-none"
            />
          </div>

          {error && <p className="text-sm text-accent">{error}</p>}

          <button
            type="submit"
            disabled={submitting || !selectedVideoId || !scheduledAt}
            className="rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
          >
            Créer la séance
          </button>
        </form>
      )}
    </div>
  );
}
