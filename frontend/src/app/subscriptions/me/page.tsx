"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { ApiError, cancelSubscription, checkoutSubscription, formatApiError, getMySubscription } from "@/lib/api";
import type { Subscription, SubscriptionStatus } from "@/lib/types";

const STATUS_LABEL: Record<SubscriptionStatus, string> = {
  pending: "En attente de paiement",
  trialing: "Période d'essai",
  active: "Active",
  past_due: "Paiement en retard",
  canceled: "Annulée",
  expired: "Expirée",
};

function formatDate(iso: string | null) {
  if (!iso) return null;
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" }).format(new Date(iso));
}

export default function MySubscriptionPage() {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
        const data = await getMySubscription(token);
        if (!cancelled) setSubscription(data);
      } catch (err) {
        if (!cancelled && !(err instanceof ApiError && err.status === 404)) {
          setError(formatApiError(err, "Impossible de charger ton abonnement."));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, getValidAccessToken]);

  async function handlePay() {
    setBusy(true);
    setError(null);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      const payment = await checkoutSubscription(token);
      window.location.href = payment.payment_url;
    } catch (err) {
      setError(formatApiError(err, "Impossible d'initier le paiement."));
      setBusy(false);
    }
  }

  async function handleCancel() {
    setBusy(true);
    setError(null);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      const updated = await cancelSubscription(token);
      setSubscription(updated);
    } catch (err) {
      setError(formatApiError(err, "Impossible d'annuler l'abonnement."));
    } finally {
      setBusy(false);
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

  if (!subscription) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Aucun abonnement</h1>
        <Link
          href="/subscriptions"
          className="mt-5 inline-block rounded-full bg-accent px-6 py-2 font-semibold text-white transition hover:bg-accent-hover"
        >
          Voir les formules
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Mon abonnement</h1>

      <div className="mt-6 rounded-lg bg-surface p-5 ring-1 ring-white/5">
        <p className="text-lg font-semibold text-foreground">{subscription.plan.name}</p>
        <p className="mt-1 text-sm text-muted">{STATUS_LABEL[subscription.status]}</p>

        {subscription.status === "trialing" && subscription.trial_end && (
          <p className="mt-3 text-sm text-muted">Essai jusqu&apos;au {formatDate(subscription.trial_end)}</p>
        )}
        {subscription.current_period_end && (
          <p className="mt-1 text-sm text-muted">
            {subscription.auto_renew ? "Renouvellement" : "Accès jusqu'au"} le{" "}
            {formatDate(subscription.current_period_end)}
          </p>
        )}
        {subscription.canceled_at && (
          <p className="mt-1 text-sm text-muted">Annulé le {formatDate(subscription.canceled_at)}</p>
        )}

        {error && <p className="mt-4 text-sm text-accent">{error}</p>}

        <div className="mt-5 flex gap-3">
          {subscription.status === "pending" && (
            <button
              type="button"
              onClick={handlePay}
              disabled={busy}
              className="rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
            >
              Payer maintenant
            </button>
          )}
          {(subscription.status === "active" || subscription.status === "trialing") && subscription.auto_renew && (
            <button
              type="button"
              onClick={handleCancel}
              disabled={busy}
              className="rounded-full border border-white/10 px-6 py-2.5 text-foreground transition hover:border-accent hover:text-accent disabled:opacity-60"
            >
              Annuler le renouvellement
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
