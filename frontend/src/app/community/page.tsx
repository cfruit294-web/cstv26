"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { createPost, formatApiError, getPosts } from "@/lib/api";
import type { Post } from "@/lib/types";
import NewReleasesSidebar from "@/components/NewReleasesSidebar";
import PostCard from "@/components/PostCard";

export default function CommunityPage() {
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  const [content, setContent] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      queueMicrotask(() => setLoading(false));
      return;
    }
    let cancelled = false;
    (async () => {
      const token = await getValidAccessToken();
      if (!token || cancelled) return;
      try {
        const page = await getPosts(token);
        if (!cancelled) setPosts(page.results);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, getValidAccessToken]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    setError(null);
    setPosting(true);
    try {
      const token = await getValidAccessToken();
      if (!token || !user) return;
      const created = await createPost({ content: content.trim(), image: image ?? undefined }, token);
      // La création ne renvoie que id/content/image : on complète avec ce qu'on connaît déjà
      // (l'utilisateur courant, des compteurs à zéro) plutôt que de refaire un aller-retour.
      const post: Post = {
        id: created.id,
        content: created.content,
        image: created.image,
        author_id: user.id,
        author_email: user.email,
        likes_count: 0,
        comments_count: 0,
        is_liked_by_me: false,
        created_at: new Date().toISOString(),
      };
      setPosts((prev) => [post, ...prev]);
      setContent("");
      setImage(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(formatApiError(err, "Impossible de publier."));
    } finally {
      setPosting(false);
    }
  }

  function handleDeleted(id: string) {
    setPosts((prev) => prev.filter((p) => p.id !== id));
  }

  if (authLoading || loading) {
    return <p className="px-4 py-24 text-center text-muted">Chargement...</p>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Connexion requise</h1>
        <p className="mt-3 text-muted">Connecte-toi pour voir et publier dans la communauté.</p>
        <Link
          href="/login"
          className="mt-5 inline-block rounded-full bg-accent px-6 py-2 font-semibold text-white transition hover:bg-accent-hover"
        >
          Se connecter
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-foreground">Communauté</h1>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          <form onSubmit={handleSubmit} className="rounded-lg bg-surface p-4 ring-1 ring-white/5">
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Quoi de neuf ?"
              rows={3}
              maxLength={2000}
              className="w-full resize-none rounded-lg border border-white/10 bg-background px-4 py-2.5 text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
            <div className="mt-3 flex items-center justify-between">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={(e) => setImage(e.target.files?.[0] ?? null)}
                className="text-sm text-muted"
              />
              <button
                type="submit"
                disabled={posting || !content.trim()}
                className="rounded-full bg-accent px-6 py-2 font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
              >
                Publier
              </button>
            </div>
            {error && <p className="mt-2 text-sm text-accent">{error}</p>}
          </form>

          <div className="mt-6 space-y-4">
            {posts.length === 0 ? (
              <p className="text-muted">Aucune publication pour l&apos;instant. Sois le premier à écrire !</p>
            ) : (
              posts.map((post) => <PostCard key={post.id} post={post} onDeleted={handleDeleted} />)
            )}
          </div>
        </div>

        <div className="lg:sticky lg:top-20 lg:h-fit">
          <NewReleasesSidebar />
        </div>
      </div>
    </div>
  );
}
