import Link from "next/link";
import MovieCard from "@/components/MovieCard";
import type { Movie } from "@/lib/types";

export default function PaginatedMovieGrid({
  movies,
  page,
  hasNext,
  hasPrevious,
  basePath,
  emptyMessage,
}: {
  movies: Movie[];
  page: number;
  hasNext: boolean;
  hasPrevious: boolean;
  basePath: string;
  emptyMessage: string;
}) {
  if (movies.length === 0) {
    return <p className="mt-6 text-muted">{emptyMessage}</p>;
  }

  return (
    <>
      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
        {movies.map((movie) => (
          <MovieCard key={movie.id} movie={movie} />
        ))}
      </div>

      {(hasPrevious || hasNext) && (
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link
            href={`${basePath}?page=${page - 1}`}
            aria-disabled={!hasPrevious}
            className={`rounded-full border border-white/10 px-5 py-2 text-sm transition ${
              hasPrevious ? "text-foreground hover:border-accent hover:text-accent" : "pointer-events-none text-muted/40"
            }`}
          >
            Précédent
          </Link>
          <span className="text-sm text-muted">Page {page}</span>
          <Link
            href={`${basePath}?page=${page + 1}`}
            aria-disabled={!hasNext}
            className={`rounded-full border border-white/10 px-5 py-2 text-sm transition ${
              hasNext ? "text-foreground hover:border-accent hover:text-accent" : "pointer-events-none text-muted/40"
            }`}
          >
            Suivant
          </Link>
        </div>
      )}
    </>
  );
}
