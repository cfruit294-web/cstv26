"use client";

import Image from "next/image";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { useCart } from "@/context/CartContext";
import { getProduct } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import type { Product } from "@/lib/types";

function formatPrice(product: Product) {
  return `${new Intl.NumberFormat("fr-FR").format(Number(product.price))} ${product.currency}`;
}

export default function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { addItem } = useCart();
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getProduct(id);
        if (!cancelled) setProduct(data);
      } catch {
        if (!cancelled) setError("Produit introuvable.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return <p className="px-4 py-24 text-center text-muted">Chargement...</p>;
  }

  if (error || !product) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">{error ?? "Produit introuvable"}</h1>
        <Link href="/shop" className="mt-4 inline-block text-accent hover:underline">
          Retour à la boutique
        </Link>
      </div>
    );
  }

  const cover = resolveMediaUrl(product.cover_image);
  const maxQuantity =
    product.product_type === "physical" && product.stock_quantity != null ? product.stock_quantity : 99;

  function handleAddToCart() {
    if (!product) return;
    addItem(product, quantity);
    setAdded(true);
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="grid gap-8 sm:grid-cols-2">
        <div className="relative aspect-square overflow-hidden rounded-lg bg-surface ring-1 ring-white/5">
          {cover ? (
            <Image src={cover} alt={product.name} fill sizes="(max-width: 640px) 100vw, 400px" className="object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center px-3 text-center text-muted">{product.name}</div>
          )}
        </div>

        <div>
          <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-muted">
            {product.product_type === "digital" ? "Numérique" : "Physique"}
          </span>
          {product.category && (
            <span className="ml-2 rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted">{product.category.name}</span>
          )}

          <h1 className="mt-3 text-2xl font-bold text-foreground">{product.name}</h1>
          <p className="mt-2 text-xl font-semibold text-accent">{formatPrice(product)}</p>

          {product.description && <p className="mt-4 whitespace-pre-line text-muted">{product.description}</p>}

          <p className="mt-4 text-sm text-muted">
            {product.is_in_stock
              ? product.product_type === "physical" && product.stock_quantity != null
                ? `${product.stock_quantity} en stock`
                : "Disponible"
              : "Épuisé"}
          </p>

          {product.is_in_stock && (
            <div className="mt-6 flex items-center gap-3">
              <div className="flex items-center rounded-full border border-white/10">
                <button
                  type="button"
                  onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                  className="px-3 py-2 text-foreground hover:text-accent"
                  aria-label="Diminuer la quantité"
                >
                  −
                </button>
                <span className="w-8 text-center text-foreground">{quantity}</span>
                <button
                  type="button"
                  onClick={() => setQuantity((q) => Math.min(maxQuantity, q + 1))}
                  className="px-3 py-2 text-foreground hover:text-accent"
                  aria-label="Augmenter la quantité"
                >
                  +
                </button>
              </div>
              <button
                type="button"
                onClick={handleAddToCart}
                className="flex-1 rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover"
              >
                Ajouter au panier
              </button>
            </div>
          )}

          {added && (
            <p className="mt-3 text-sm text-muted">
              Ajouté au panier.{" "}
              <Link href="/cart" className="text-accent hover:underline">
                Voir le panier
              </Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
