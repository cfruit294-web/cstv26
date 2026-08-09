"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getWatchlistStatus, toggleWatchlist } from "@/lib/api";

export default function WatchlistButton({ movieId }: { movieId: string }) {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [inWatchlist, setInWatchlist] = useState(false);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (authLoading || !user) return;
    let cancelled = false;
    (async () => {
      const token = await getValidAccessToken();
      if (!token || cancelled) return;
      try {
        const { in_watchlist } = await getWatchlistStatus(movieId, token);
        if (!cancelled) setInWatchlist(in_watchlist);
      } catch {
        // Statut indisponible : le bouton reste utilisable, juste sans état initial fiable.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, movieId, getValidAccessToken]);

  async function handleClick() {
    const token = await getValidAccessToken();
    if (!token || pending) return;
    setPending(true);
    try {
      const { in_watchlist } = await toggleWatchlist(movieId, token);
      setInWatchlist(in_watchlist);
    } finally {
      setPending(false);
    }
  }

  const baseClass =
    "rounded-full border border-white/15 px-5 py-2.5 text-sm font-semibold text-foreground transition hover:border-accent hover:text-accent disabled:opacity-60";

  if (!authLoading && !user) {
    return (
      <Link href="/login" className={baseClass}>
        + Ma liste
      </Link>
    );
  }

  return (
    <button type="button" onClick={handleClick} disabled={pending} className={baseClass}>
      {inWatchlist ? "✓ Dans ma liste" : "+ Ma liste"}
    </button>
  );
}
