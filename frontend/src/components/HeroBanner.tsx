import Link from "next/link";
import type { Movie } from "@/lib/types";

export default function HeroBanner({ movie }: { movie: Movie }) {
  const backdrop = movie.poster_url && movie.poster_url !== "N/A" ? movie.poster_url : null;

  return (
    <section className="relative flex h-[60vh] min-h-96 items-end overflow-hidden">
      {backdrop && (
        <div
          className="absolute inset-0 bg-cover bg-top opacity-40 blur-xs"
          style={{ backgroundImage: `url(${backdrop})` }}
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-background via-background/60 to-transparent" />
      <div className="relative mx-auto w-full max-w-7xl px-4 pb-10 sm:px-6">
        <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-accent">
          {movie.type === "series" ? "Série à la une" : "Film à la une"}
        </p>
        <h1 className="max-w-2xl text-3xl font-extrabold text-white sm:text-5xl">{movie.title}</h1>
        <p className="mt-3 max-w-xl text-sm text-muted sm:text-base line-clamp-3">{movie.plot}</p>
        <div className="mt-5 flex gap-3">
          <Link
            href={`/movies/${movie.id}`}
            className="rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover"
          >
            Voir la fiche
          </Link>
        </div>
      </div>
    </section>
  );
}
