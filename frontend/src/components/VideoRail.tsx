"use client";

import { useMemo, useRef, useState } from "react";
import MovieCard from "@/components/MovieCard";
import CategoryPills from "@/components/CategoryPills";
import type { Movie } from "@/lib/types";

const ALL = "Tous";
const MAX_GENRES = 6;

function extractGenres(movies: Movie[]) {
  const counts = new Map<string, number>();
  for (const movie of movies) {
    for (const raw of movie.genre.split(",")) {
      const genre = raw.trim();
      if (!genre) continue;
      counts.set(genre, (counts.get(genre) ?? 0) + 1);
    }
  }
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([genre]) => genre);
  return [ALL, ...sorted.slice(0, MAX_GENRES)];
}

export default function VideoRail({ movies, emptyMessage }: { movies: Movie[]; emptyMessage: string }) {
  const categories = useMemo(() => extractGenres(movies), [movies]);
  const [active, setActive] = useState(ALL);
  const scrollerRef = useRef<HTMLDivElement>(null);

  const filtered =
    active === ALL
      ? movies
      : movies.filter((movie) => movie.genre.toLowerCase().includes(active.toLowerCase()));

  function scrollNext() {
    scrollerRef.current?.scrollBy({ left: 480, behavior: "smooth" });
  }

  return (
    <div>
      <CategoryPills categories={categories} active={active} onChange={setActive} />

      {filtered.length === 0 ? (
        <p className="mt-6 text-muted">{emptyMessage}</p>
      ) : (
        <div className="relative mt-4">
          <div ref={scrollerRef} className="no-scrollbar flex gap-4 overflow-x-auto pb-2">
            {filtered.map((movie) => (
              <div key={movie.id} className="w-40 shrink-0 sm:w-48">
                <MovieCard movie={movie} />
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={scrollNext}
            aria-label="Voir plus"
            className="absolute -right-3 top-1/3 hidden h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20 sm:flex"
          >
            &rsaquo;
          </button>
        </div>
      )}
    </div>
  );
}
