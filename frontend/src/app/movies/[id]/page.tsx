import Image from "next/image";
import { notFound } from "next/navigation";
import { ApiError, getMovie, getMovieRecommendations } from "@/lib/api";
import MovieVideosSection from "@/components/MovieVideosSection";
import MovieRow from "@/components/MovieRow";
import WatchlistButton from "@/components/WatchlistButton";
import ShareButton from "@/components/ShareButton";

export default async function MovieDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let movie;
  try {
    movie = await getMovie(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  let recommendations: Awaited<ReturnType<typeof getMovieRecommendations>>["results"] = [];
  try {
    recommendations = (await getMovieRecommendations(id)).results;
  } catch {
    recommendations = [];
  }

  const hasPoster = movie.poster_url && movie.poster_url !== "N/A";
  const genres = movie.genre
    ? movie.genre.split(",").map((g) => g.trim()).filter(Boolean)
    : [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <div className="flex flex-col gap-8 sm:flex-row">
        <div className="relative aspect-2/3 w-48 shrink-0 overflow-hidden rounded-lg bg-surface ring-1 ring-white/5 sm:w-64">
          {hasPoster ? (
            <Image src={movie.poster_url} alt={movie.title} fill className="object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center px-3 text-center text-sm text-muted">
              {movie.title}
            </div>
          )}
        </div>

        <div className="flex-1">
          <h1 className="text-3xl font-extrabold text-foreground">{movie.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted">
            <span>{movie.year}</span>
            {movie.runtime_minutes && <span>{movie.runtime_minutes} min</span>}
            {movie.rated && (
              <span className="rounded border border-white/15 px-1.5 py-0.5 text-xs">{movie.rated}</span>
            )}
            {movie.imdb_rating && <span className="text-yellow-400">★ {movie.imdb_rating}</span>}
          </div>

          {genres.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {genres.map((g) => (
                <span key={g} className="rounded-full bg-surface-2 px-3 py-1 text-xs text-foreground">
                  {g}
                </span>
              ))}
            </div>
          )}

          <p className="mt-4 max-w-2xl text-foreground/90">{movie.plot}</p>

          <div className="mt-5 flex flex-wrap gap-3">
            <WatchlistButton movieId={movie.id} />
            <ShareButton title={movie.title} />
          </div>

          <dl className="mt-6 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
            {movie.director && (
              <div>
                <dt className="text-muted">Réalisateur</dt>
                <dd className="text-foreground">{movie.director}</dd>
              </div>
            )}
            {movie.actors && (
              <div>
                <dt className="text-muted">Distribution</dt>
                <dd className="text-foreground">{movie.actors}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      <div className="mt-10">
        <h2 className="mb-3 text-lg font-semibold text-foreground">Regarder</h2>
        <MovieVideosSection movieId={movie.id} />
      </div>

      <div className="mt-10">
        <MovieRow title="Pour vous" movies={recommendations} />
      </div>
    </div>
  );
}
