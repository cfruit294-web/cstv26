"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getOrders } from "@/lib/api";
import type { Order, OrderStatus } from "@/lib/types";

const STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "En attente de paiement",
  paid: "Payée",
  canceled: "Annulée",
  refunded: "Remboursée",
};

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" }).format(new Date(iso));
}

export default function OrdersPage() {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
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
        const page = await getOrders(token);
        if (!cancelled) setOrders(page.results);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, getValidAccessToken]);

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

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Mes commandes</h1>

      {orders.length === 0 ? (
        <p className="mt-6 text-muted">
          Aucune commande pour l&apos;instant.{" "}
          <Link href="/shop" className="text-accent hover:underline">
            Découvrir la boutique
          </Link>
        </p>
      ) : (
        <ul className="mt-6 divide-y divide-white/5">
          {orders.map((order) => (
            <li key={order.id}>
              <Link href={`/orders/${order.id}`} className="flex items-center justify-between gap-4 py-4 hover:text-accent">
                <div>
                  <p className="font-medium text-foreground">Commande du {formatDate(order.created_at)}</p>
                  <p className="text-sm text-muted">
                    {order.items.length} article{order.items.length > 1 ? "s" : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium text-foreground">
                    {new Intl.NumberFormat("fr-FR").format(Number(order.total_amount))} {order.currency}
                  </p>
                  <p
                    className={`text-sm ${order.status === "paid" ? "text-accent" : "text-muted"}`}
                  >
                    {STATUS_LABEL[order.status]}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
