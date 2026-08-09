"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMovies } from "@/lib/api";
import type { Movie } from "@/lib/types";
import MovieCard from "@/components/MovieCard";

export default function NewReleasesSidebar() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const page = await getMovies({ ordering: "-created_at", page: 1 });
        if (!cancelled) setMovies(page.results.slice(0, 6));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading || movies.length === 0) return null;

  return (
    <aside className="rounded-lg bg-surface p-4 ring-1 ring-white/5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">Nouveaux films &amp; séries</h2>
        <Link href="/movies" className="text-xs text-muted hover:text-accent">
          Tout voir
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {movies.map((movie) => (
          <MovieCard key={movie.id} movie={movie} />
        ))}
      </div>
    </aside>
  );
}
