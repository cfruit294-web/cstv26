"use client";

import { useState } from "react";

export default function ShareButton({ title }: { title: string }) {
  const [copied, setCopied] = useState(false);

  async function handleClick() {
    const url = window.location.href;

    if (navigator.share) {
      try {
        await navigator.share({ title, url });
      } catch {
        // L'utilisateur a annulé le partage natif : rien à faire.
      }
      return;
    }

    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="rounded-full border border-white/15 px-5 py-2.5 text-sm font-semibold text-foreground transition hover:border-accent hover:text-accent"
    >
      {copied ? "Lien copié !" : "Partager"}
    </button>
  );
}
