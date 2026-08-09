import { getMovies } from "@/lib/api";
import PaginatedMovieGrid from "@/components/PaginatedMovieGrid";

export default async function SeriesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const { page: pageParam } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);

  let data;
  try {
    data = await getMovies({ type: "series", page });
  } catch {
    data = { count: 0, next: null, previous: null, results: [] };
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Séries</h1>
      <PaginatedMovieGrid
        movies={data.results}
        page={page}
        hasNext={Boolean(data.next)}
        hasPrevious={Boolean(data.previous)}
        basePath="/series"
        emptyMessage="Aucune série dans le catalogue pour l'instant."
      />
    </div>
  );
}
