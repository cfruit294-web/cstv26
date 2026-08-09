import Link from "next/link";
import { getCategories, getProducts } from "@/lib/api";
import type { Category, Paginated, Product, ProductType } from "@/lib/types";
import ProductCard from "@/components/ProductCard";
import ShopFilters from "@/components/ShopFilters";

function buildHref(current: { category?: string; type?: string; q?: string }, page: number) {
  const params = new URLSearchParams();
  if (current.category) params.set("category", current.category);
  if (current.type) params.set("type", current.type);
  if (current.q) params.set("q", current.q);
  if (page > 1) params.set("page", String(page));
  const qs = params.toString();
  return `/shop${qs ? `?${qs}` : ""}`;
}

export default async function ShopPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; category?: string; type?: string; q?: string }>;
}) {
  const { page: pageParam, category, type, q } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);
  const productType: ProductType | undefined = type === "digital" || type === "physical" ? type : undefined;

  let categories: Category[] = [];
  let products: Paginated<Product> = { count: 0, next: null, previous: null, results: [] };
  let apiError = false;

  try {
    const [categoriesPage, productsPage] = await Promise.all([
      getCategories(),
      getProducts({ page, category, type: productType, q }),
    ]);
    categories = categoriesPage.results;
    products = productsPage;
  } catch {
    apiError = true;
  }

  if (apiError) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Boutique indisponible</h1>
        <p className="mt-3 text-muted">Impossible de contacter l&apos;API pour le moment.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Boutique</h1>
      <ShopFilters categories={categories} selectedCategory={category} selectedType={productType} query={q} />

      {products.results.length === 0 ? (
        <p className="mt-6 text-muted">Aucun produit ne correspond à ta recherche.</p>
      ) : (
        <>
          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {products.results.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>

          {(products.previous || products.next) && (
            <div className="mt-8 flex items-center justify-center gap-4">
              <Link
                href={buildHref({ category, type: productType, q }, page - 1)}
                aria-disabled={!products.previous}
                className={`rounded-full border border-white/10 px-5 py-2 text-sm transition ${
                  products.previous
                    ? "text-foreground hover:border-accent hover:text-accent"
                    : "pointer-events-none text-muted/40"
                }`}
              >
                Précédent
              </Link>
              <span className="text-sm text-muted">Page {page}</span>
              <Link
                href={buildHref({ category, type: productType, q }, page + 1)}
                aria-disabled={!products.next}
                className={`rounded-full border border-white/10 px-5 py-2 text-sm transition ${
                  products.next
                    ? "text-foreground hover:border-accent hover:text-accent"
                    : "pointer-events-none text-muted/40"
                }`}
              >
                Suivant
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}
