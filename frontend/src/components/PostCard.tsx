"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { createConversation, deletePost, togglePostLike } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import type { Post } from "@/lib/types";

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(
    new Date(iso),
  );
}

export default function PostCard({
  post,
  onDeleted,
  linkToDetail = true,
}: {
  post: Post;
  onDeleted?: (id: string) => void;
  linkToDetail?: boolean;
}) {
  const { user, getValidAccessToken } = useAuth();
  const router = useRouter();
  const [liked, setLiked] = useState(post.is_liked_by_me);
  const [likesCount, setLikesCount] = useState(post.likes_count);
  const [busy, setBusy] = useState(false);
  const image = resolveMediaUrl(post.image);
  const isMine = user?.email === post.author_email;

  async function handleLike() {
    const token = await getValidAccessToken();
    if (!token) return;
    setLiked((v) => !v);
    setLikesCount((c) => (liked ? c - 1 : c + 1));
    try {
      const result = await togglePostLike(post.id, token);
      setLiked(result.liked);
      setLikesCount(result.likes_count);
    } catch {
      setLiked((v) => !v);
      setLikesCount((c) => (liked ? c + 1 : c - 1));
    }
  }

  async function handleDelete() {
    const token = await getValidAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      await deletePost(post.id, token);
      onDeleted?.(post.id);
    } finally {
      setBusy(false);
    }
  }

  async function handleMessage() {
    const token = await getValidAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      const conversation = await createConversation([post.author_id], token);
      router.push(`/messages/${conversation.id}`);
    } finally {
      setBusy(false);
    }
  }

  const content = (
    <>
      <p className="text-sm text-muted">
        {post.author_email} · {formatDate(post.created_at)}
      </p>
      <p className="mt-2 whitespace-pre-line text-foreground">{post.content}</p>
      {image && (
        <div className="relative mt-3 aspect-video overflow-hidden rounded-lg bg-surface-2">
          <Image src={image} alt="" fill sizes="600px" className="object-cover" />
        </div>
      )}
    </>
  );

  return (
    <div className="rounded-lg bg-surface p-4 ring-1 ring-white/5">
      {linkToDetail ? (
        <Link href={`/community/${post.id}`} className="block hover:opacity-90">
          {content}
        </Link>
      ) : (
        content
      )}

      <div className="mt-3 flex items-center gap-4 text-sm text-muted">
        <button
          type="button"
          onClick={handleLike}
          className={`flex items-center gap-1 transition hover:text-accent ${liked ? "text-accent" : ""}`}
        >
          {liked ? "♥" : "♡"} {likesCount}
        </button>
        {linkToDetail ? (
          <Link href={`/community/${post.id}`} className="hover:text-foreground">
            {post.comments_count} commentaire{post.comments_count > 1 ? "s" : ""}
          </Link>
        ) : (
          <span>
            {post.comments_count} commentaire{post.comments_count > 1 ? "s" : ""}
          </span>
        )}

        {!isMine && (
          <button type="button" onClick={handleMessage} disabled={busy} className="ml-auto hover:text-accent disabled:opacity-60">
            Envoyer un message
          </button>
        )}
        {isMine && (
          <button
            type="button"
            onClick={handleDelete}
            disabled={busy}
            className="ml-auto hover:text-accent disabled:opacity-60"
          >
            Supprimer
          </button>
        )}
      </div>
    </div>
  );
}
