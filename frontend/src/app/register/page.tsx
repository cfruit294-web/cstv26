"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";

export default function RegisterPage() {
  const { register } = useAuth();

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password, passwordConfirm, fullName || undefined);
      setSuccess(true);
    } catch (err) {
      setError(formatApiError(err, "Échec de l'inscription."));
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="mx-auto max-w-sm px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-foreground">Compte créé</h1>
        <p className="mt-3 text-muted">
          Vérifie ta boîte mail pour confirmer ton adresse, puis{" "}
          <Link href="/login" className="text-accent hover:underline">
            connecte-toi
          </Link>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-16">
      <h1 className="text-2xl font-bold text-foreground">Créer un compte</h1>
      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <input
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Nom complet"
          className="rounded-lg border border-white/10 bg-surface px-4 py-2.5 text-foreground focus:border-accent focus:outline-none"
        />
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          className="rounded-lg border border-white/10 bg-surface px-4 py-2.5 text-foreground focus:border-accent focus:outline-none"
          required
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Mot de passe"
          className="rounded-lg border border-white/10 bg-surface px-4 py-2.5 text-foreground focus:border-accent focus:outline-none"
          required
        />
        <input
          type="password"
          value={passwordConfirm}
          onChange={(e) => setPasswordConfirm(e.target.value)}
          placeholder="Confirme le mot de passe"
          className="rounded-lg border border-white/10 bg-surface px-4 py-2.5 text-foreground focus:border-accent focus:outline-none"
          required
        />
        {error && <p className="text-sm text-accent">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
        >
          S&apos;inscrire
        </button>
      </form>
      <p className="mt-6 text-sm text-muted">
        Déjà un compte ?{" "}
        <Link href="/login" className="text-accent hover:underline">
          Connecte-toi
        </Link>
      </p>
    </div>
  );
}
