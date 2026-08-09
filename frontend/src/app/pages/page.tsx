import Link from "next/link";
import { getPages } from "@/lib/api";
import type { CmsPage, PageType } from "@/lib/types";

const TYPE_LABEL: Record<PageType, string> = {
  landing: "Accueil",
  blog: "Blog",
  faq: "FAQ",
  legal: "Mentions légales",
};

function formatDate(iso: string | null) {
  if (!iso) return null;
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" }).format(new Date(iso));
}

export default async function PagesIndex() {
  let pages: CmsPage[] = [];
  let apiError = false;

  try {
    const result = await getPages();
    pages = result.results;
  } catch {
    apiError = true;
  }

  if (apiError) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Service indisponible</h1>
        <p className="mt-3 text-muted">Impossible de charger les pages pour le moment.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Pages</h1>

      {pages.length === 0 ? (
        <p className="mt-6 text-muted">Aucune page publiée pour l&apos;instant.</p>
      ) : (
        <ul className="mt-6 divide-y divide-white/5">
          {pages.map((page) => (
            <li key={page.id}>
              <Link href={`/pages/${page.slug}`} className="flex items-center justify-between gap-4 py-4 hover:text-accent">
                <div>
                  <p className="font-medium text-foreground">{page.title}</p>
                  <p className="text-sm text-muted">
                    {TYPE_LABEL[page.page_type]}
                    {page.published_at && ` · ${formatDate(page.published_at)}`}
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
