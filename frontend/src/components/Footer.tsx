import Link from "next/link";
import { API_BASE_URL, SERVER_FORWARDED_HEADERS } from "@/lib/config";
import type { CmsPage, PageType } from "@/lib/types";

// Fetch dédié (plutôt que lib/api.ts, qui force `cache: "no-store"` sur tout) : ces liens changent
// rarement, un cache revalidé toutes les heures évite de rendre l'app entière dynamique juste pour
// le footer, qui est présent sur chaque page.
async function getFooterPages(type: PageType): Promise<CmsPage[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/cms/pages/?type=${type}`, {
      headers: SERVER_FORWARDED_HEADERS,
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.results as CmsPage[];
  } catch {
    return [];
  }
}

export default async function Footer() {
  const [legal, faq] = await Promise.all([getFooterPages("legal"), getFooterPages("faq")]);
  const legalPages = [...legal, ...faq];

  return (
    <footer className="mt-16 border-t border-white/5 py-8 text-sm text-muted">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <p>CSTV &mdash; plateforme de streaming vidéo.</p>
        {legalPages.length > 0 && (
          <nav className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
            {legalPages.map((page) => (
              <Link key={page.id} href={`/pages/${page.slug}`} className="hover:text-foreground">
                {page.title}
              </Link>
            ))}
          </nav>
        )}
      </div>
    </footer>
  );
}
