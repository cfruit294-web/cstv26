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
  startAt,
  onProgress,
}: {
  src: string;
  poster?: string | null;
  subtitles?: VideoPlayerSubtitle[];
  /** Position (en secondes) à laquelle reprendre la lecture, si le navigateur a chargé les métadonnées. */
  startAt?: number;
  /** Appelé au fil de la lecture (environ toutes les 10s) et à la pause, pour sauvegarder la progression. */
  onProgress?: (currentTime: number) => void;
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

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !startAt || startAt < 1) return;

    const resume = () => {
      video.currentTime = startAt;
    };
    video.addEventListener("loadedmetadata", resume, { once: true });
    return () => video.removeEventListener("loadedmetadata", resume);
  }, [src, startAt]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !onProgress) return;

    let lastReported = 0;
    const reportIfDue = () => {
      if (Math.abs(video.currentTime - lastReported) >= 10) {
        lastReported = video.currentTime;
        onProgress(video.currentTime);
      }
    };
    const reportNow = () => onProgress(video.currentTime);

    video.addEventListener("timeupdate", reportIfDue);
    video.addEventListener("pause", reportNow);
    return () => {
      video.removeEventListener("timeupdate", reportIfDue);
      video.removeEventListener("pause", reportNow);
    };
  }, [onProgress]);

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
