import Image from "next/image";
import Link from "next/link";
import { resolveMediaUrl } from "@/lib/media";
import type { LiveStream } from "@/lib/types";

function formatSchedule(iso: string | null) {
  if (!iso) return null;
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function LiveCard({ stream }: { stream: LiveStream }) {
  const thumbnail = resolveMediaUrl(stream.replay?.thumbnail ?? null);
  const schedule = formatSchedule(stream.scheduled_at);

  return (
    <Link href={`/live/${stream.id}`} className="group block w-full">
      <div className="relative aspect-video overflow-hidden rounded-lg bg-surface ring-1 ring-white/5 transition group-hover:ring-accent">
        {thumbnail ? (
          <Image
            src={thumbnail}
            alt={stream.title}
            fill
            sizes="(max-width: 640px) 240px, 320px"
            className="object-cover transition duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center px-3 text-center text-sm text-muted">
            {stream.title}
          </div>
        )}

        {stream.status === "live" && (
          <span className="absolute left-1.5 top-1.5 flex items-center gap-1 rounded-md bg-accent px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" />
            En direct
          </span>
        )}
        {stream.status === "scheduled" && schedule && (
          <span className="absolute left-1.5 top-1.5 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-foreground">
            {schedule}
          </span>
        )}
        {stream.status === "ended" && stream.replay?.status === "ready" && (
          <span className="absolute left-1.5 top-1.5 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-foreground">
            ▶ Revoir
          </span>
        )}
      </div>
      <p className="mt-2 truncate text-sm font-medium text-foreground group-hover:text-accent">
        {stream.title}
      </p>
    </Link>
  );
}
