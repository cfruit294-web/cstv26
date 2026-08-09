import { getMovies } from "@/lib/api";
import type { Movie } from "@/lib/types";
import MovieCard from "@/components/MovieCard";

export default async function TopPage() {
  let movies: Movie[];
  try {
    const data = await getMovies({ ordering: "-imdb_rating", page: 1 });
    movies = data.results.filter((m) => m.imdb_rating);
  } catch {
    movies = [];
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Les mieux notés</h1>
      <p className="mt-1 text-sm text-muted">Classement basé sur la note IMDb.</p>

      {movies.length === 0 ? (
        <p className="mt-6 text-muted">Pas encore assez de titres notés pour établir un classement.</p>
      ) : (
        <div className="mt-8 grid grid-cols-2 gap-x-4 gap-y-10 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {movies.map((movie, index) => (
            <MovieCard key={movie.id} movie={movie} rank={index + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
