"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Category, ProductType } from "@/lib/types";

export default function ShopFilters({
  categories,
  selectedCategory,
  selectedType,
  query,
}: {
  categories: Category[];
  selectedCategory?: string;
  selectedType?: ProductType;
  query?: string;
}) {
  const router = useRouter();
  const [search, setSearch] = useState(query ?? "");

  function navigate(overrides: { category?: string; type?: string; q?: string }) {
    const merged = { category: selectedCategory, type: selectedType, q: query, ...overrides };
    const params = new URLSearchParams();
    if (merged.category) params.set("category", merged.category);
    if (merged.type) params.set("type", merged.type);
    if (merged.q) params.set("q", merged.q);
    const qs = params.toString();
    router.push(`/shop${qs ? `?${qs}` : ""}`);
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    navigate({ q: search.trim() || undefined });
  }

  return (
    <div className="mt-4 flex flex-wrap items-center gap-3">
      <form onSubmit={handleSearchSubmit} className="min-w-[200px] flex-1">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          type="search"
          placeholder="Rechercher un produit..."
          className="w-full rounded-full border border-white/10 bg-surface px-4 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
        />
      </form>

      <select
        value={selectedType ?? ""}
        onChange={(e) => navigate({ type: e.target.value || undefined })}
        className="rounded-full border border-white/10 bg-surface px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
      >
        <option value="">Tous les types</option>
        <option value="digital">Numérique</option>
        <option value="physical">Physique</option>
      </select>

      <select
        value={selectedCategory ?? ""}
        onChange={(e) => navigate({ category: e.target.value || undefined })}
        className="rounded-full border border-white/10 bg-surface px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
      >
        <option value="">Toutes les catégories</option>
        {categories.map((c) => (
          <option key={c.id} value={c.slug}>
            {c.name}
          </option>
        ))}
      </select>
    </div>
  );
}
