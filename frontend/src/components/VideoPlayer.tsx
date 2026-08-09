"use client";

import Hls from "hls.js";
import { useEffect, useRef, useState } from "react";

export interface VideoPlayerSubtitle {
  language: string;
  label: string;
  url: string;
}

export default function VideoPlayer({
  src,
  poster,
  subtitles,
}: {
  src: string;
  poster?: string | null;
  subtitles?: VideoPlayerSubtitle[];
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    setError(null);

    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src;
      return;
    }

    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(video);
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          setError("Impossible de lire cette vidéo pour le moment.");
        }
      });
      return () => hls.destroy();
    }

    queueMicrotask(() => setError("Ton navigateur ne supporte pas la lecture HLS."));
  }, [src]);

  return (
    <div className="w-full overflow-hidden rounded-lg bg-black">
      <video
        ref={videoRef}
        controls
        poster={poster ?? undefined}
        className="aspect-video w-full"
      >
        {subtitles?.map((subtitle) => (
          <track
            key={subtitle.language}
            kind="subtitles"
            srcLang={subtitle.language}
            label={subtitle.label}
            src={subtitle.url}
          />
        ))}
      </video>
      {error && <p className="p-3 text-sm text-accent">{error}</p>}
    </div>
  );
}
