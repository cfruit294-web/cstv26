"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useCart } from "@/context/CartContext";
import { checkoutOrder, createOrder, formatApiError } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";

export default function CartPage() {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const { items, removeItem, setQuantity, clear } = useCart();
  const router = useRouter();

  const [shippingAddress, setShippingAddress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const hasPhysicalItem = items.some((item) => item.product.product_type === "physical");
  const total = useMemo(
    () => items.reduce((sum, item) => sum + Number(item.product.price) * item.quantity, 0),
    [items],
  );
  const currency = items[0]?.product.currency ?? "XOF";

  async function handleCheckout() {
    if (!user) {
      router.push("/login");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        router.push("/login");
        return;
      }
      const order = await createOrder(
        {
          items: items.map((item) => ({ product_id: item.product.id, quantity: item.quantity })),
          shipping_address: shippingAddress,
        },
        token,
      );
      const payment = await checkoutOrder(order.id, token);
      clear();
      window.location.href = payment.payment_url;
    } catch (err) {
      setError(formatApiError(err, "Impossible de finaliser la commande."));
      setSubmitting(false);
    }
  }

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Ton panier est vide</h1>
        <Link href="/shop" className="mt-4 inline-block text-accent hover:underline">
          Découvrir la boutique
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Panier</h1>

      <ul className="mt-6 divide-y divide-white/5">
        {items.map((item) => {
          const cover = resolveMediaUrl(item.product.cover_image);
          return (
            <li key={item.product.id} className="flex items-center gap-4 py-4">
              <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-md bg-surface-2">
                {cover && <Image src={cover} alt={item.product.name} fill sizes="64px" className="object-cover" />}
              </div>
              <div className="min-w-0 flex-1">
                <Link href={`/shop/${item.product.id}`} className="truncate font-medium text-foreground hover:text-accent">
                  {item.product.name}
                </Link>
                <p className="text-sm text-muted">
                  {new Intl.NumberFormat("fr-FR").format(Number(item.product.price))} {item.product.currency}
                </p>
              </div>
              <div className="flex items-center rounded-full border border-white/10">
                <button
                  type="button"
                  onClick={() => setQuantity(item.product.id, item.quantity - 1)}
                  className="px-3 py-1.5 text-foreground hover:text-accent"
                  aria-label="Diminuer la quantité"
                >
                  −
                </button>
                <span className="w-8 text-center text-sm text-foreground">{item.quantity}</span>
                <button
                  type="button"
                  onClick={() => setQuantity(item.product.id, item.quantity + 1)}
                  className="px-3 py-1.5 text-foreground hover:text-accent"
                  aria-label="Augmenter la quantité"
                >
                  +
                </button>
              </div>
              <p className="w-24 shrink-0 text-right text-sm font-medium text-foreground">
                {new Intl.NumberFormat("fr-FR").format(Number(item.product.price) * item.quantity)} {item.product.currency}
              </p>
              <button
                type="button"
                onClick={() => removeItem(item.product.id)}
                className="shrink-0 text-sm text-muted hover:text-accent"
                aria-label="Retirer du panier"
              >
                Retirer
              </button>
            </li>
          );
        })}
      </ul>

      {hasPhysicalItem && (
        <div className="mt-6">
          <label className="text-sm font-medium text-foreground">Adresse de livraison</label>
          <textarea
            value={shippingAddress}
            onChange={(e) => setShippingAddress(e.target.value)}
            rows={3}
            placeholder="Adresse complète de livraison"
            className="mt-2 w-full rounded-lg border border-white/10 bg-surface px-4 py-2.5 text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
          />
        </div>
      )}

      <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4">
        <span className="text-lg font-semibold text-foreground">Total</span>
        <span className="text-lg font-semibold text-foreground">
          {new Intl.NumberFormat("fr-FR").format(total)} {currency}
        </span>
      </div>

      {error && <p className="mt-4 text-sm text-accent">{error}</p>}

      <button
        type="button"
        onClick={handleCheckout}
        disabled={submitting || authLoading}
        className="mt-6 w-full rounded-full bg-accent px-6 py-3 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
      >
        {user ? "Passer commande" : "Se connecter pour commander"}
      </button>
    </div>
  );
}
