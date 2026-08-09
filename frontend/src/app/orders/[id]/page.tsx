"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { formatApiError, getOrder, getOrderDownload } from "@/lib/api";
import type { Order, OrderStatus } from "@/lib/types";

const STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "En attente de paiement",
  paid: "Payée",
  canceled: "Annulée",
  refunded: "Remboursée",
};

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(
    new Date(iso),
  );
}

export default function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

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
        const data = await getOrder(id, token);
        if (!cancelled) setOrder(data);
      } catch {
        if (!cancelled) setError("Commande introuvable.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, id, getValidAccessToken]);

  async function handleDownload(productId: string) {
    setDownloadError(null);
    setDownloadingId(productId);
    try {
      const token = await getValidAccessToken();
      if (!token || !order) return;
      const { download_url } = await getOrderDownload(order.id, productId, token);
      window.open(download_url, "_blank");
    } catch (err) {
      setDownloadError(formatApiError(err, "Téléchargement impossible pour le moment."));
    } finally {
      setDownloadingId(null);
    }
  }

  if (authLoading || loading) {
    return <p className="px-4 py-24 text-center text-muted">Chargement...</p>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Connexion requise</h1>
        <Link href="/login" className="mt-4 inline-block text-accent hover:underline">
          Se connecter
        </Link>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">{error ?? "Commande introuvable"}</h1>
        <Link href="/orders" className="mt-4 inline-block text-accent hover:underline">
          Retour à mes commandes
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <Link href="/orders" className="text-sm text-muted hover:text-accent">
        &larr; Mes commandes
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-foreground">Commande du {formatDate(order.created_at)}</h1>
      <p className={`mt-1 text-sm ${order.status === "paid" ? "text-accent" : "text-muted"}`}>
        {STATUS_LABEL[order.status]}
      </p>

      <ul className="mt-6 divide-y divide-white/5">
        {order.items.map((item) => (
          <li key={item.id} className="flex items-center justify-between gap-4 py-4">
            <div className="min-w-0">
              <p className="truncate font-medium text-foreground">{item.product.name}</p>
              <p className="text-sm text-muted">
                {item.quantity} × {new Intl.NumberFormat("fr-FR").format(Number(item.unit_price))} {order.currency}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-4">
              <p className="font-medium text-foreground">
                {new Intl.NumberFormat("fr-FR").format(item.subtotal)} {order.currency}
              </p>
              {order.status === "paid" && item.product.product_type === "digital" && (
                <button
                  type="button"
                  onClick={() => handleDownload(item.product.id)}
                  disabled={downloadingId === item.product.id}
                  className="rounded-full border border-white/10 px-4 py-1.5 text-sm text-foreground transition hover:border-accent hover:text-accent disabled:opacity-60"
                >
                  {downloadingId === item.product.id ? "..." : "Télécharger"}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      {downloadError && <p className="mt-4 text-sm text-accent">{downloadError}</p>}

      <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4">
        <span className="text-lg font-semibold text-foreground">Total</span>
        <span className="text-lg font-semibold text-foreground">
          {new Intl.NumberFormat("fr-FR").format(Number(order.total_amount))} {order.currency}
        </span>
      </div>

      {order.shipping_address && (
        <div className="mt-6">
          <p className="text-sm font-medium text-foreground">Adresse de livraison</p>
          <p className="mt-1 whitespace-pre-line text-sm text-muted">{order.shipping_address}</p>
        </div>
      )}
    </div>
  );
}
