"use client";

import Link from "next/link";
import { use, useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getMessages, markConversationRead } from "@/lib/api";
import { WS_BASE_URL } from "@/lib/config";
import type { Message } from "@/lib/types";

function formatTime(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

type IncomingEvent =
  | { type: "message"; id: string; sender_email: string; content: string; created_at: string }
  | { type: "typing"; user_email: string }
  | { type: "presence"; user_email: string; status: "online" | "offline" };

export default function ConversationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, isLoading: authLoading, getValidAccessToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [connected, setConnected] = useState(false);
  const [typingUser, setTypingUser] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

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
        const page = await getMessages(id, token);
        if (cancelled) return;
        setMessages(page.results);
        markConversationRead(id, token).catch(() => {});
      } catch {
        if (!cancelled) setError("Conversation introuvable.");
        setLoading(false);
        return;
      }
      if (cancelled) return;
      setLoading(false);

      const socket = new WebSocket(`${WS_BASE_URL}/ws/messaging/${id}/?token=${token}`);
      socketRef.current = socket;

      socket.onopen = () => setConnected(true);
      socket.onclose = () => setConnected(false);
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data) as IncomingEvent;
        if (data.type === "message") {
          setMessages((prev) => [
            ...prev,
            {
              id: data.id,
              sender_email: data.sender_email,
              content: data.content,
              attachment: null,
              is_read_by_me: true,
              created_at: data.created_at,
            },
          ]);
        } else if (data.type === "typing") {
          setTypingUser(data.user_email);
          if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
          typingTimeoutRef.current = setTimeout(() => setTypingUser(null), 3000);
        }
      };
    })();

    return () => {
      cancelled = true;
      socketRef.current?.close();
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    };
  }, [authLoading, user, id, getValidAccessToken]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const content = draft.trim();
    if (!content || socketRef.current?.readyState !== WebSocket.OPEN) return;
    socketRef.current.send(JSON.stringify({ content }));
    setDraft("");
  }

  function handleTyping(value: string) {
    setDraft(value);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "typing" }));
    }
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

  if (error) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">{error}</h1>
        <Link href="/messages" className="mt-4 inline-block text-accent hover:underline">
          Retour aux messages
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-2xl flex-col px-4 py-4 sm:px-6">
      <Link href="/messages" className="text-sm text-muted hover:text-accent">
        &larr; Messages
      </Link>

      <div className="mt-3 flex-1 space-y-2 overflow-y-auto">
        {messages.map((message) => {
          const mine = message.sender_email === user.email;
          return (
            <div key={message.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2 ${
                  mine ? "bg-accent text-white" : "bg-surface text-foreground"
                }`}
              >
                <p className="whitespace-pre-line text-sm">{message.content}</p>
                <p className={`mt-1 text-[10px] ${mine ? "text-white/70" : "text-muted"}`}>
                  {formatTime(message.created_at)}
                </p>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {typingUser && <p className="mt-1 text-xs text-muted">{typingUser} est en train d&apos;écrire...</p>}

      <form onSubmit={handleSend} className="mt-3 flex gap-2">
        <input
          value={draft}
          onChange={(e) => handleTyping(e.target.value)}
          placeholder={connected ? "Écrire un message..." : "Connexion..."}
          disabled={!connected}
          className="flex-1 rounded-full border border-white/10 bg-surface px-4 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={!connected || !draft.trim()}
          className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-white transition hover:bg-accent-hover disabled:opacity-60"
        >
          Envoyer
        </button>
      </form>
    </div>
  );
}
