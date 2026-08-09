import Link from "next/link";
import { getLiveStreams } from "@/lib/api";
import type { LiveStream } from "@/lib/types";

function timelineTimestamp(stream: LiveStream) {
  return stream.scheduled_at ?? stream.started_at ?? stream.created_at;
}

function dayKey(iso: string) {
  return new Date(iso).toISOString().slice(0, 10);
}

function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function formatDayLabel(iso: string) {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);

  const formatted = new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(date);

  if (isSameDay(date, today)) return `Aujourd'hui — ${formatted}`;
  if (isSameDay(date, yesterday)) return `Hier — ${formatted}`;
  if (isSameDay(date, tomorrow)) return `Demain — ${formatted}`;
  return formatted;
}

function formatTime(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

const STATUS_LABEL: Record<LiveStream["status"], string> = {
  live: "En direct",
  scheduled: "Programmé",
  ended: "Revoir",
  canceled: "Annulé",
};

export default async function ProgrammePage() {
  let streams: LiveStream[] = [];
  let apiError = false;

  try {
    const page = await getLiveStreams();
    streams = page.results;
  } catch {
    apiError = true;
  }

  if (apiError) {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-foreground">Service indisponible</h1>
        <p className="mt-3 text-muted">Impossible de charger le programme pour le moment.</p>
      </div>
    );
  }

  const sorted = [...streams].sort(
    (a, b) => new Date(timelineTimestamp(b)).getTime() - new Date(timelineTimestamp(a)).getTime(),
  );

  const groups = new Map<string, LiveStream[]>();
  for (const stream of sorted) {
    const key = dayKey(timelineTimestamp(stream));
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(stream);
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="mb-6 text-2xl font-bold text-foreground">Programme</h1>

      {groups.size === 0 && <p className="text-muted">Aucun live programmé pour le moment.</p>}

      <div className="space-y-8">
        {[...groups.entries()].map(([key, dayStreams]) => (
          <section key={key}>
            <h2 className="mb-3 border-b border-white/10 pb-2 text-sm font-semibold uppercase tracking-wide text-muted">
              {formatDayLabel(timelineTimestamp(dayStreams[0]))}
            </h2>
            <ul className="divide-y divide-white/5">
              {[...dayStreams]
                .sort((a, b) => new Date(timelineTimestamp(a)).getTime() - new Date(timelineTimestamp(b)).getTime())
                .map((stream) => (
                  <li key={stream.id}>
                    <Link
                      href={`/live/${stream.id}`}
                      className="flex items-center justify-between gap-4 py-3 transition hover:text-accent"
                    >
                      <span className="flex items-center gap-4">
                        <span className="w-14 shrink-0 text-sm text-muted">
                          {formatTime(timelineTimestamp(stream))}
                        </span>
                        <span className="font-medium text-foreground">{stream.title}</span>
                      </span>
                      <span
                        className={
                          stream.status === "live"
                            ? "shrink-0 rounded-full bg-accent px-2.5 py-0.5 text-xs font-bold uppercase text-white"
                            : "shrink-0 text-xs text-muted"
                        }
                      >
                        {STATUS_LABEL[stream.status]}
                      </span>
                    </Link>
                  </li>
                ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
