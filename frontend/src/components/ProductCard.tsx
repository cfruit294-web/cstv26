import Image from "next/image";
import Link from "next/link";
import { resolveMediaUrl } from "@/lib/media";
import type { Product } from "@/lib/types";

function formatPrice(product: Product) {
  return `${new Intl.NumberFormat("fr-FR").format(Number(product.price))} ${product.currency}`;
}

export default function ProductCard({ product }: { product: Product }) {
  const cover = resolveMediaUrl(product.cover_image);

  return (
    <Link href={`/shop/${product.id}`} className="group block w-full">
      <div className="relative aspect-square overflow-hidden rounded-lg bg-surface ring-1 ring-white/5 transition group-hover:ring-accent">
        {cover ? (
          <Image
            src={cover}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 160px, 220px"
            className="object-cover transition duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center px-3 text-center text-sm text-muted">
            {product.name}
          </div>
        )}

        <span className="absolute left-1.5 top-1.5 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-foreground">
          {product.product_type === "digital" ? "Numérique" : "Physique"}
        </span>

        {!product.is_in_stock && (
          <span className="absolute right-1.5 top-1.5 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-accent">
            Épuisé
          </span>
        )}
      </div>
      <p className="mt-2 truncate text-sm font-medium text-foreground group-hover:text-accent">{product.name}</p>
      <p className="text-xs text-muted">{formatPrice(product)}</p>
    </Link>
  );
}
