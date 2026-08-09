import Link from "next/link";

export default function PaymentReturnPage() {
  return (
    <div className="mx-auto max-w-lg px-4 py-24 text-center">
      <h1 className="text-2xl font-bold text-foreground">Paiement en cours de vérification</h1>
      <p className="mt-3 text-muted">
        Nous confirmons ton paiement avec CinetPay. Cela prend généralement quelques secondes —
        consulte ton abonnement pour voir le statut mis à jour.
      </p>
      <Link
        href="/subscriptions/me"
        className="mt-6 inline-block rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover"
      >
        Voir mon abonnement
      </Link>
    </div>
  );
}
