"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { createConversation, searchUsers } from "@/lib/api";
import type { UserSearchResult } from "@/lib/types";

export default function NewConversationSearch({ onClose }: { onClose: () => void }) {
  const { getValidAccessToken } = useAuth();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [starting, setStarting] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      const page = await searchUsers(q, token);
      setResults(page.results);
      setHasSearched(true);
    } finally {
      setSearching(false);
    }
  }

  async function handleStart(userId: string) {
    setStarting(true);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      const conversation = await createConversation([userId], token);
      router.push(`/messages/${conversation.id}`);
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="rounded-lg bg-surface p-4 ring-1 ring-white/5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">Nouvelle conversation</p>
        <button type="button" onClick={onClose} className="text-sm text-muted hover:text-accent">
          Fermer
        </button>
      </div>

      <form onSubmit={handleSearch} className="mt-3 flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher par email ou nom..."
          className="flex-1 rounded-full border border-white/10 bg-background px-4 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={searching || !query.trim()}
          className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
        >
          Chercher
        </button>
      </form>

      {results.length > 0 && (
        <ul className="mt-3 divide-y divide-white/5">
          {results.map((result) => (
            <li key={result.id} className="flex items-center justify-between gap-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{result.full_name || result.email}</p>
                {result.full_name && <p className="truncate text-xs text-muted">{result.email}</p>}
              </div>
              <button
                type="button"
                onClick={() => handleStart(result.id)}
                disabled={starting}
                className="shrink-0 rounded-full border border-white/10 px-4 py-1.5 text-sm text-foreground transition hover:border-accent hover:text-accent disabled:opacity-60"
              >
                Écrire
              </button>
            </li>
          ))}
        </ul>
      )}
      {searching && <p className="mt-3 text-sm text-muted">Recherche...</p>}
      {!searching && hasSearched && results.length === 0 && (
        <p className="mt-3 text-sm text-muted">Aucun utilisateur trouvé.</p>
      )}
    </div>
  );
}
