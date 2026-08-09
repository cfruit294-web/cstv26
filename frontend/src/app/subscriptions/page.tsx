"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { checkoutSubscription, formatApiError, getPlans, subscribeToPlan } from "@/lib/api";
import type { BillingPeriod, Plan } from "@/lib/types";

const BILLING_LABEL: Record<BillingPeriod, string> = {
  weekly: "semaine",
  monthly: "mois",
  yearly: "an",
};

function formatPrice(plan: Plan) {
  return `${new Intl.NumberFormat("fr-FR").format(Number(plan.price))} ${plan.currency} / ${BILLING_LABEL[plan.billing_period]}`;
}

export default function SubscriptionsPage() {
  const { user, getValidAccessToken } = useAuth();
  const router = useRouter();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyPlanId, setBusyPlanId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const page = await getPlans();
        setPlans(page.results);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function handleSubscribeClick(e: React.MouseEvent<HTMLButtonElement>) {
    const planId = e.currentTarget.dataset.planId;
    const plan = plans.find((p) => p.id === planId);
    if (plan) handleSubscribe(plan);
  }

  async function handleSubscribe(plan: Plan) {
    if (!user) {
      router.push("/login");
      return;
    }
    setError(null);
    setNotice(null);
    setBusyPlanId(plan.id);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      const subscription = await subscribeToPlan(plan.id, token);

      if (subscription.status === "trialing") {
        setNotice("Essai gratuit activé ! Retrouve les détails sur ta page d'abonnement.");
        return;
      }

      const payment = await checkoutSubscription(token);
      window.location.href = payment.payment_url;
    } catch (err) {
      setError(formatApiError(err, "Impossible de souscrire à cette formule."));
    } finally {
      setBusyPlanId(null);
    }
  }

  if (loading) {
    return <p className="px-4 py-24 text-center text-muted">Chargement...</p>;
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Abonnements</h1>
      <p className="mt-2 text-muted">
        Choisis une formule pour débloquer le contenu premium.{" "}
        {user && (
          <Link href="/subscriptions/me" className="text-accent hover:underline">
            Voir mon abonnement
          </Link>
        )}
      </p>

      {error && <p className="mt-4 text-sm text-accent">{error}</p>}
      {notice && <p className="mt-4 text-sm text-foreground">{notice}</p>}

      {plans.length === 0 ? (
        <p className="mt-6 text-muted">Aucune formule disponible pour l&apos;instant.</p>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan) => (
            <div key={plan.id} className="flex flex-col rounded-lg bg-surface p-5 ring-1 ring-white/5">
              <span className="w-fit rounded-md bg-surface-2 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-muted">
                {plan.tier}
              </span>
              <h2 className="mt-3 text-lg font-semibold text-foreground">{plan.name}</h2>
              <p className="mt-1 text-xl font-bold text-accent">{formatPrice(plan)}</p>
              {plan.trial_days > 0 && (
                <p className="mt-1 text-sm text-muted">{plan.trial_days} jours d&apos;essai gratuit</p>
              )}
              {plan.description && <p className="mt-3 text-sm text-muted">{plan.description}</p>}

              {plan.features.length > 0 && (
                <ul className="mt-4 space-y-1.5 text-sm text-foreground">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <span className="text-accent">✓</span>
                      {feature}
                    </li>
                  ))}
                </ul>
              )}

              <button
                type="button"
                data-plan-id={plan.id}
                onClick={handleSubscribeClick}
                disabled={busyPlanId === plan.id}
                className="mt-6 rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
              >
                {user ? "Souscrire" : "Se connecter pour souscrire"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
