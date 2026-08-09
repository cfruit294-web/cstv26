import Image from "next/image";
import Link from "next/link";
import type { Movie } from "@/lib/types";

function hasPoster(url: string) {
  return Boolean(url) && url !== "N/A";
}

const TYPE_LABELS: Record<Movie["type"], string> = {
  movie: "Film",
  series: "Série",
  episode: "Épisode",
};

export default function MovieCard({ movie, rank }: { movie: Movie; rank?: number }) {
  const genres = movie.genre
    ? movie.genre.split(",").map((g) => g.trim()).filter(Boolean).slice(0, 2)
    : [];

  return (
    <Link href={`/movies/${movie.id}`} className="group block w-full">
      <div className="relative aspect-2/3 overflow-hidden rounded-lg bg-surface ring-1 ring-white/5 transition group-hover:ring-accent">
        {hasPoster(movie.poster_url) ? (
          <Image
            src={movie.poster_url}
            alt={movie.title}
            fill
            sizes="(max-width: 640px) 160px, 192px"
            className="object-cover transition duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center px-3 text-center text-sm text-muted">
            {movie.title}
          </div>
        )}

        <span className="absolute left-1.5 top-1.5 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-foreground">
          {TYPE_LABELS[movie.type]}
        </span>

        {movie.imdb_rating && (
          <span className="absolute right-1.5 top-1.5 rounded-md bg-black/70 px-1.5 py-0.5 text-xs font-semibold text-yellow-400">
            ★ {movie.imdb_rating}
          </span>
        )}

        {rank && (
          <span
            className="absolute -bottom-1 -left-1 select-none text-6xl font-black italic text-black/80 [-webkit-text-stroke:2px_var(--accent)]"
            style={{ WebkitTextStroke: "2px var(--accent)" }}
          >
            {rank}
          </span>
        )}
      </div>
      <p className="mt-2 truncate text-sm font-medium text-foreground group-hover:text-accent">
        {movie.title}
      </p>
      <div className="flex items-center gap-2 text-xs text-muted">
        <span>{movie.year}</span>
        {genres.map((g) => (
          <span key={g} className="truncate rounded-full bg-surface-2 px-2 py-0.5">
            {g}
          </span>
        ))}
      </div>
    </Link>
  );
}
