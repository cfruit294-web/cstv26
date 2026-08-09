import { getLiveStreams, getMovies } from "@/lib/api";
import type { LiveStream, Movie } from "@/lib/types";
import HeroBanner from "@/components/HeroBanner";
import LiveRow from "@/components/LiveRow";
import MovieRow from "@/components/MovieRow";

const LIVE_STATUS_PRIORITY: Record<LiveStream["status"], number> = {
  live: 0,
  scheduled: 1,
  ended: 2,
  canceled: 3,
};

export default async function HomePage() {
  let movies: Movie[] = [];
  let apiError = false;

  try {
    const page = await getMovies({ page: 1 });
    movies = page.results;
  } catch {
    apiError = true;
  }

  let liveStreams: LiveStream[] = [];
  try {
    const page = await getLiveStreams();
    liveStreams = [...page.results]
      .sort((a, b) => LIVE_STATUS_PRIORITY[a.status] - LIVE_STATUS_PRIORITY[b.status])
      .slice(0, 10);
  } catch {
    // Le live est secondaire : la home reste utilisable même si cet appel échoue.
  }

  if (apiError) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Service indisponible</h1>
        <p className="mt-3 text-muted">
          Impossible de contacter l&apos;API CSTV. Vérifie que le serveur Django tourne bien.
        </p>
      </div>
    );
  }

  if (movies.length === 0) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Le catalogue est vide</h1>
        <p className="mt-3 text-muted">
          Importe des films depuis l&apos;admin (
          <code className="text-foreground">POST /api/v1/catalog/movies/import/</code>) pour peupler
          la page d&apos;accueil.
        </p>
      </div>
    );
  }

  const films = movies.filter((m) => m.type === "movie");
  const series = movies.filter((m) => m.type === "series");
  const topRated = [...movies]
    .filter((m) => m.imdb_rating)
    .sort((a, b) => Number(b.imdb_rating) - Number(a.imdb_rating))
    .slice(0, 10);
  const featured = movies[0];

  return (
    <div>
      <HeroBanner movie={featured} />
      <div className="py-8">
        <MovieRow title="Les mieux notés" movies={topRated} ranked moreHref="/top" />
        <LiveRow streams={liveStreams} />
        <MovieRow title="Ajoutés récemment" movies={movies} />
        <MovieRow title="Films" movies={films} moreHref="/movies" />
        <MovieRow title="Séries" movies={series} moreHref="/series" />
      </div>
    </div>
  );
}
