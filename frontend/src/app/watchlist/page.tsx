"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getWatchlist } from "@/lib/api";
import type { WatchlistItem } from "@/lib/types";
import MovieCard from "@/components/MovieCard";

export default function WatchlistPage() {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [items, setItems] = useState<WatchlistItem[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      queueMicrotask(() => setLoading(false));
      return;
    }
    let cancelled = false;
    (async () => {
      const token = await getValidAccessToken();
      if (!token || cancelled) return;
      try {
        const page = await getWatchlist(token);
        if (!cancelled) setItems(page.results);
      } catch {
        if (!cancelled) setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, getValidAccessToken]);

  if (!authLoading && !user) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Connexion requise</h1>
        <p className="mt-3 text-muted">Connecte-toi pour voir ta liste.</p>
        <Link
          href="/login"
          className="mt-5 inline-block rounded-full bg-accent px-6 py-2 font-semibold text-white transition hover:bg-accent-hover"
        >
          Se connecter
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Ma liste</h1>

      {authLoading || loading ? (
        <p className="mt-6 text-muted">Chargement...</p>
      ) : !items || items.length === 0 ? (
        <p className="mt-6 text-muted">Ta liste est vide pour l&apos;instant.</p>
      ) : (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {items.map((item) => (
            <MovieCard key={item.id} movie={item.movie} />
          ))}
        </div>
      )}
    </div>
  );
}
