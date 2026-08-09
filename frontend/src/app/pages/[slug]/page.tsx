import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, getPage } from "@/lib/api";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  try {
    const page = await getPage(slug);
    return {
      title: page.meta_title || page.title,
      description: page.meta_description || undefined,
    };
  } catch {
    return {};
  }
}

export default async function CmsPagePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  let page;
  try {
    page = await getPage(slug);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
      <Link href="/pages" className="text-sm text-muted hover:text-accent">
        &larr; Pages
      </Link>
      <h1 className="mt-2 text-3xl font-extrabold text-foreground">{page.title}</h1>
      <div className="mt-6 whitespace-pre-line text-foreground/90">{page.content}</div>
    </div>
  );
}
