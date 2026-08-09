"use client";

import { useEffect, useRef, useState } from "react";
import type { Ad } from "@/lib/types";

const DEFAULT_IMAGE_DURATION = 5;

export default function AdBreak({ ad, onFinished }: { ad: Ad; onFinished: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const durationSeconds = ad.duration_seconds ?? (ad.creative_type === "image" ? DEFAULT_IMAGE_DURATION : null);
  const hasUsableMedia = (ad.creative_type === "video" && ad.video_file) || (ad.creative_type === "image" && ad.image);
  const [remaining, setRemaining] = useState(durationSeconds ?? 0);

  useEffect(() => {
    if (!hasUsableMedia) {
      onFinished();
      return;
    }
    if (!durationSeconds) return;
    queueMicrotask(() => setRemaining(durationSeconds));
    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onFinished();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ad.id, durationSeconds, hasUsableMedia]);

  return (
    <div className="relative w-full overflow-hidden rounded-lg bg-black">
      <span className="absolute left-3 top-3 z-10 rounded-md bg-black/70 px-2 py-1 text-xs font-semibold text-white">
        Publicité{remaining > 0 ? ` · ${remaining}s` : ""}
      </span>

      {ad.creative_type === "video" && ad.video_file ? (
        <video
          ref={videoRef}
          src={ad.video_file}
          autoPlay
          muted
          playsInline
          className="aspect-video w-full"
          onEnded={onFinished}
        />
      ) : ad.image ? (
        <a
          href={ad.click_url || undefined}
          target={ad.click_url ? "_blank" : undefined}
          rel={ad.click_url ? "noopener noreferrer" : undefined}
          className="block aspect-video w-full"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={ad.image} alt={ad.title} className="h-full w-full object-cover" />
        </a>
      ) : (
        <div className="aspect-video w-full" />
      )}
    </div>
  );
}
