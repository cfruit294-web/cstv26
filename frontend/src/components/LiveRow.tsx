import Link from "next/link";
import LiveCard from "@/components/LiveCard";
import type { LiveStream } from "@/lib/types";

export default function LiveRow({ streams }: { streams: LiveStream[] }) {
  if (streams.length === 0) return null;

  return (
    <section className="mb-10">
      <div className="mb-3 flex items-center justify-between px-4 sm:px-6">
        <h2 className="text-lg font-semibold text-foreground">Live</h2>
        <Link href="/programme" className="text-sm text-muted transition hover:text-accent">
          Voir le programme &rarr;
        </Link>
      </div>
      <div className="no-scrollbar flex gap-4 overflow-x-auto px-4 pb-2 sm:px-6">
        {streams.map((stream) => (
          <div key={stream.id} className="w-64 shrink-0 sm:w-72">
            <LiveCard stream={stream} />
          </div>
        ))}
      </div>
    </section>
  );
}
