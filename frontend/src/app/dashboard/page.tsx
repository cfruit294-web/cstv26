"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getDashboardOverview } from "@/lib/api";
import type { DashboardOverview } from "@/lib/types";
import RoleBarChart from "@/components/RoleBarChart";
import StatTile from "@/components/StatTile";

const numberFormat = new Intl.NumberFormat("fr-FR");

function formatAmount(value: string) {
  const n = Number(value);
  return `${numberFormat.format(Number.isFinite(n) ? n : 0)} XOF`;
}

export default function DashboardPage() {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user || user.role !== "admin") {
      queueMicrotask(() => setLoading(false));
      return;
    }
    let cancelled = false;
    (async () => {
      const token = await getValidAccessToken();
      if (!token || cancelled) return;
      try {
        const overview = await getDashboardOverview(token);
        if (!cancelled) setData(overview);
      } catch {
        if (!cancelled) setError("Impossible de charger les statistiques.");
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

  if (!user || user.role !== "admin") {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Accès réservé</h1>
        <p className="mt-3 text-muted">Cette page est réservée aux administrateurs.</p>
        <Link href="/" className="mt-4 inline-block text-accent hover:underline">
          Retour à l&apos;accueil
        </Link>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">{error ?? "Statistiques indisponibles"}</h1>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <h1 className="mb-6 text-2xl font-bold text-foreground">Tableau de bord</h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <StatTile
          label="Utilisateurs"
          value={numberFormat.format(data.users.total)}
          sublabel={`dont ${numberFormat.format(data.users.new_last_30_days)} sur les 30 derniers jours`}
        />
        <StatTile
          label="Abonnements actifs"
          value={numberFormat.format(data.subscriptions.active)}
          sublabel={`${numberFormat.format(data.subscriptions.total)} au total`}
        />
        <StatTile
          label="Revenu total"
          value={formatAmount(data.revenue.total)}
          sublabel={`${formatAmount(data.revenue.last_30_days)} sur les 30 derniers jours`}
        />
        <StatTile
          label="Paiements réussis"
          value={numberFormat.format(data.revenue.successful_payments)}
        />
        <StatTile
          label="Vidéos"
          value={numberFormat.format(data.videos.total)}
          sublabel={`${numberFormat.format(data.videos.ready)} prêtes · ${numberFormat.format(data.videos.processing)} en traitement`}
        />
        <StatTile
          label="Lives en cours"
          value={numberFormat.format(data.live.currently_live)}
          sublabel={`${numberFormat.format(data.live.total)} au total`}
        />
        <StatTile
          label="Commandes payées"
          value={numberFormat.format(data.orders.paid)}
          sublabel={`${numberFormat.format(data.orders.total)} au total`}
        />
        <StatTile
          label="Produits actifs"
          value={numberFormat.format(data.products.active)}
          sublabel={`${numberFormat.format(data.products.total)} au total`}
        />
        <StatTile label="Posts communauté" value={numberFormat.format(data.community.posts)} />
        <StatTile label="Messages échangés" value={numberFormat.format(data.messaging.messages)} />
      </div>

      <div className="mt-6">
        <RoleBarChart byRole={data.users.by_role} />
      </div>
    </div>
  );
}
