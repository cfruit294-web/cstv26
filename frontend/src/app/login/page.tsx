"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";

export default function LoginPage() {
  const { login, loginTwoFactor } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [preAuthToken, setPreAuthToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await login(email, password);
      if (result.twoFactorRequired && result.preAuthToken) {
        setPreAuthToken(result.preAuthToken);
      } else {
        router.push("/");
      }
    } catch (err) {
      setError(formatApiError(err, "Échec de la connexion."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTwoFactor(e: React.FormEvent) {
    e.preventDefault();
    if (!preAuthToken) return;
    setError(null);
    setSubmitting(true);
    try {
      await loginTwoFactor(preAuthToken, code);
      router.push("/");
    } catch {
      setError("Code de vérification invalide.");
    } finally {
      setSubmitting(false);
    }
  }

  if (preAuthToken) {
    return (
      <div className="mx-auto max-w-sm px-4 py-16">
        <h1 className="text-2xl font-bold text-foreground">Vérification en deux étapes</h1>
        <p className="mt-2 text-sm text-muted">Entre le code généré par ton application d&apos;authentification.</p>
        <form onSubmit={handleTwoFactor} className="mt-6 flex flex-col gap-4">
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Code à 6 chiffres"
            className="rounded-lg border border-white/10 bg-surface px-4 py-2.5 text-foreground focus:border-accent focus:outline-none"
            required
          />
          {error && <p className="text-sm text-accent">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
          >
            Valider
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-16">
      <h1 className="text-2xl font-bold text-foreground">Connexion</h1>
      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
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
        {error && <p className="text-sm text-accent">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-full bg-accent px-6 py-2.5 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
        >
          Se connecter
        </button>
      </form>
      <p className="mt-6 text-sm text-muted">
        Pas de compte ?{" "}
        <Link href="/register" className="text-accent hover:underline">
          Inscris-toi
        </Link>
      </p>
    </div>
  );
}
