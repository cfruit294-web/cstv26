import Link from "next/link";
import MovieCard from "@/components/MovieCard";
import type { Movie } from "@/lib/types";

export default function MovieRow({
  title,
  movies,
  ranked = false,
  moreHref,
}: {
  title: string;
  movies: Movie[];
  ranked?: boolean;
  moreHref?: string;
}) {
  if (movies.length === 0) return null;

  return (
    <section className="mb-10">
      <div className="mb-3 flex items-center justify-between px-4 sm:px-6">
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        {moreHref && (
          <Link href={moreHref} className="text-sm text-muted transition hover:text-accent">
            Voir plus &rarr;
          </Link>
        )}
      </div>
      <div className="no-scrollbar flex gap-4 overflow-x-auto px-4 pb-2 sm:px-6">
        {movies.map((movie, index) => (
          <div key={movie.id} className={`shrink-0 ${ranked ? "w-32 sm:w-40" : "w-40 sm:w-48"}`}>
            <MovieCard movie={movie} rank={ranked ? index + 1 : undefined} />
          </div>
        ))}
      </div>
    </section>
  );
}
