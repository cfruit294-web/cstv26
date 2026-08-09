import Link from "next/link";
import { getLiveStreams, getMovies } from "@/lib/api";
import type { LiveStream } from "@/lib/types";
import LiveHero from "@/components/LiveHero";
import VideoRail from "@/components/VideoRail";

const STATUS_PRIORITY: Record<LiveStream["status"], number> = {
  live: 0,
  scheduled: 1,
  ended: 2,
  canceled: 3,
};

export default async function LivePage() {
  let featured: LiveStream | null = null;
  try {
    const page = await getLiveStreams();
    const sorted = [...page.results].sort(
      (a, b) => STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status],
    );
    featured = sorted[0] ?? null;
  } catch {
    featured = null;
  }

  let movies: Awaited<ReturnType<typeof getMovies>>["results"] = [];
  try {
    const page = await getMovies({ page: 1 });
    movies = page.results;
  } catch {
    movies = [];
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <LiveHero stream={featured} />

      <section className="mt-10">
        <h2 className="mb-4 text-lg font-semibold text-foreground">À découvrir</h2>
        <VideoRail movies={movies} emptyMessage="Aucune vidéo disponible pour l'instant." />
      </section>

      <nav aria-label="Fil d'ariane" className="mt-16 border-t border-white/10 py-6 text-sm">
        <Link href="/" className="text-accent hover:underline">
          Accueil
        </Link>
        <span className="mx-2 text-muted">/</span>
        <span className="text-foreground">Live</span>
      </nav>
    </div>
  );
}
