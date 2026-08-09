"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { createComment, deleteComment, formatApiError, getComments, getPost } from "@/lib/api";
import type { Comment as CommentType, Post } from "@/lib/types";
import PostCard from "@/components/PostCard";

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(
    new Date(iso),
  );
}

export default function PostDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [post, setPost] = useState<Post | null>(null);
  const [comments, setComments] = useState<CommentType[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [commentError, setCommentError] = useState<string | null>(null);

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
        const [postData, commentsPage] = await Promise.all([getPost(id, token), getComments(id, token)]);
        if (!cancelled) {
          setPost(postData);
          setComments(commentsPage.results);
        }
      } catch {
        if (!cancelled) setError("Publication introuvable.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, id, getValidAccessToken]);

  async function handleSubmitComment(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    setCommentError(null);
    setSubmitting(true);
    try {
      const token = await getValidAccessToken();
      if (!token || !user) return;
      const created = await createComment(id, content.trim(), token);
      // La création ne renvoie que id/content : on complète avec l'utilisateur courant et
      // l'heure locale plutôt que de refaire un aller-retour.
      const comment: CommentType = {
        id: created.id,
        content: created.content,
        author_email: user.email,
        created_at: new Date().toISOString(),
      };
      setComments((prev) => [...prev, comment]);
      setContent("");
      setPost((p) => (p ? { ...p, comments_count: p.comments_count + 1 } : p));
    } catch (err) {
      setCommentError(formatApiError(err, "Impossible d'envoyer le commentaire."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteComment(commentId: string) {
    const token = await getValidAccessToken();
    if (!token) return;
    await deleteComment(commentId, token);
    setComments((prev) => prev.filter((c) => c.id !== commentId));
    setPost((p) => (p ? { ...p, comments_count: Math.max(0, p.comments_count - 1) } : p));
  }

  if (authLoading || loading) {
    return <p className="px-4 py-24 text-center text-muted">Chargement...</p>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Connexion requise</h1>
        <Link href="/login" className="mt-4 inline-block text-accent hover:underline">
          Se connecter
        </Link>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">{error ?? "Publication introuvable"}</h1>
        <Link href="/community" className="mt-4 inline-block text-accent hover:underline">
          Retour à la communauté
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <Link href="/community" className="text-sm text-muted hover:text-accent">
        &larr; Communauté
      </Link>

      <div className="mt-3">
        <PostCard post={post} linkToDetail={false} />
      </div>

      <form onSubmit={handleSubmitComment} className="mt-6 flex gap-2">
        <input
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Écrire un commentaire..."
          maxLength={1000}
          className="flex-1 rounded-full border border-white/10 bg-surface px-4 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={submitting || !content.trim()}
          className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
        >
          Envoyer
        </button>
      </form>
      {commentError && <p className="mt-2 text-sm text-accent">{commentError}</p>}

      <ul className="mt-6 space-y-4">
        {comments.map((comment) => (
          <li key={comment.id} className="rounded-lg bg-surface p-3 ring-1 ring-white/5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted">
                {comment.author_email} · {formatDate(comment.created_at)}
              </p>
              {comment.author_email === user.email && (
                <button
                  type="button"
                  onClick={() => handleDeleteComment(comment.id)}
                  className="text-xs text-muted hover:text-accent"
                >
                  Supprimer
                </button>
              )}
            </div>
            <p className="mt-1 text-foreground">{comment.content}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
