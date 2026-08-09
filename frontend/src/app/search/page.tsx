import Link from "next/link";
import { search } from "@/lib/api";
import MovieCard from "@/components/MovieCard";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const query = q?.trim() ?? "";

  if (!query) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Recherche</h1>
        <p className="mt-3 text-muted">Utilise la barre en haut pour chercher un film ou une série.</p>
      </div>
    );
  }

  let results;
  try {
    results = await search(query);
  } catch {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Recherche indisponible</h1>
        <p className="mt-3 text-muted">Impossible de contacter l&apos;API pour l&apos;instant.</p>
      </div>
    );
  }

  const hasMovies = results.movies.length > 0;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h1 className="text-xl font-semibold text-foreground">
        Résultats pour <span className="text-accent">&laquo;{query}&raquo;</span>
      </h1>

      {!hasMovies && (
        <p className="mt-6 text-muted">
          Aucun film ou série trouvé. Essaie un autre titre, ou{" "}
          <Link href="/" className="text-accent hover:underline">
            retourne à l&apos;accueil
          </Link>
          .
        </p>
      )}

      {hasMovies && (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {results.movies.map((movie) => (
            <MovieCard key={movie.id} movie={movie} />
          ))}
        </div>
      )}
    </div>
  );
}
