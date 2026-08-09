"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Dropdown from "@/components/Dropdown";
import NotificationBell from "@/components/NotificationBell";

const PRIMARY_LINKS = [
  { href: "/", label: "Accueil" },
  { href: "/subscriptions", label: "Abonnements" },
];

const DISCOVER_LINKS = [
  { href: "/movies", label: "Films" },
  { href: "/series", label: "Séries" },
  { href: "/top", label: "Les mieux notés" },
  { href: "/programme", label: "Programme" },
];

function DropdownLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="block px-4 py-2 text-sm text-muted transition hover:bg-surface-2 hover:text-foreground">
      {children}
    </Link>
  );
}

export default function Navbar() {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [query, setQuery] = useState("");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
  }

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  const discoverActive = DISCOVER_LINKS.some((link) => isActive(link.href));

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 sm:px-6">
        <Link href="/" className="shrink-0 text-xl font-extrabold tracking-tight text-white">
          CS<span className="text-accent">TV</span>
        </Link>

        <nav className="order-3 flex w-full shrink-0 items-center gap-1 overflow-x-auto text-sm sm:order-0 sm:w-auto sm:gap-2">
          {PRIMARY_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`shrink-0 rounded-full px-3 py-1.5 transition ${
                isActive(link.href) ? "bg-surface-2 text-white" : "text-muted hover:text-foreground"
              }`}
            >
              {link.label}
            </Link>
          ))}

          <Dropdown trigger={<span className={discoverActive ? "text-white" : ""}>Découvrir</span>}>
            {DISCOVER_LINKS.map((link) => (
              <DropdownLink key={link.href} href={link.href}>
                {link.label}
              </DropdownLink>
            ))}
          </Dropdown>

          {user && (
            <Link
              href="/community"
              className={`shrink-0 rounded-full px-3 py-1.5 transition ${
                isActive("/community") ? "bg-surface-2 text-white" : "text-muted hover:text-foreground"
              }`}
            >
              Communauté
            </Link>
          )}
          {user && (
            <Link
              href="/watchparty"
              className={`shrink-0 rounded-full px-3 py-1.5 transition ${
                isActive("/watchparty") ? "bg-surface-2 text-white" : "text-muted hover:text-foreground"
              }`}
            >
              Visionnage entre amis
            </Link>
          )}
        </nav>

        <form onSubmit={handleSearch} className="ml-0 flex-1 sm:ml-2">
          <div className="relative max-w-md">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              type="search"
              placeholder="Rechercher un film, une série..."
              className="w-full rounded-full border border-white/10 bg-surface px-4 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>
        </form>

        <nav className="ml-auto flex shrink-0 items-center gap-2 text-sm">
          {isLoading ? null : user ? (
            <>
              <Link href="/messages" aria-label="Messages" className="rounded-full p-2 text-foreground transition hover:text-accent">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
                  <path d="M4 4h16v12H7l-3 3V4z" />
                </svg>
              </Link>

              <NotificationBell />

              <Dropdown align="right" trigger={<span className="max-w-32 truncate">{user.full_name || user.email}</span>}>
                <DropdownLink href="/subscriptions/me">Mon abonnement</DropdownLink>
                {user.role === "admin" && <DropdownLink href="/dashboard">Tableau de bord</DropdownLink>}
                <button
                  type="button"
                  onClick={() => logout()}
                  className="block w-full px-4 py-2 text-left text-sm text-muted transition hover:bg-surface-2 hover:text-foreground"
                >
                  Déconnexion
                </button>
              </Dropdown>
            </>
          ) : (
            <>
              <Link href="/login" className="rounded-full px-4 py-1.5 text-foreground transition hover:text-accent">
                Connexion
              </Link>
              <Link
                href="/register"
                className="rounded-full bg-accent px-4 py-1.5 font-medium text-white transition hover:bg-accent-hover"
              >
                S&apos;inscrire
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
