"use client";

import Hls from "hls.js";
import { useEffect, useRef, useState } from "react";

export interface RemotePlaybackEvent {
  position: number;
  is_playing: boolean;
  nonce: number;
}

export default function SyncedVideoPlayer({
  src,
  poster,
  controllable,
  onLocalAction,
  remoteEvent,
}: {
  src: string;
  poster?: string | null;
  controllable: boolean;
  onLocalAction?: (action: "play" | "pause" | "seek", position: number) => void;
  remoteEvent: RemotePlaybackEvent | null;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const applyingRemote = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [needsGesture, setNeedsGesture] = useState(false);

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
        if (data.fatal) setError("Impossible de lire cette vidéo pour le moment.");
      });
      return () => hls.destroy();
    }
    queueMicrotask(() => setError("Ton navigateur ne supporte pas la lecture HLS."));
  }, [src]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !remoteEvent) return;

    applyingRemote.current = true;
    if (Math.abs(video.currentTime - remoteEvent.position) > 1.5) {
      video.currentTime = remoteEvent.position;
    }
    const action = remoteEvent.is_playing ? video.play() : Promise.resolve(video.pause());
    action?.then(() => setNeedsGesture(false)).catch(() => setNeedsGesture(true));

    const release = setTimeout(() => {
      applyingRemote.current = false;
    }, 400);
    return () => clearTimeout(release);
  }, [remoteEvent]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !controllable) return;

    function handlePlay() {
      if (!applyingRemote.current) onLocalAction?.("play", video!.currentTime);
    }
    function handlePause() {
      if (!applyingRemote.current) onLocalAction?.("pause", video!.currentTime);
    }
    function handleSeeked() {
      if (!applyingRemote.current) onLocalAction?.("seek", video!.currentTime);
    }

    video.addEventListener("play", handlePlay);
    video.addEventListener("pause", handlePause);
    video.addEventListener("seeked", handleSeeked);
    return () => {
      video.removeEventListener("play", handlePlay);
      video.removeEventListener("pause", handlePause);
      video.removeEventListener("seeked", handleSeeked);
    };
  }, [controllable, onLocalAction]);

  function handleManualSync() {
    const video = videoRef.current;
    if (!video || !remoteEvent) return;
    applyingRemote.current = true;
    video.currentTime = remoteEvent.position;
    video
      .play()
      .then(() => setNeedsGesture(false))
      .catch(() => setNeedsGesture(true))
      .finally(() => {
        setTimeout(() => {
          applyingRemote.current = false;
        }, 400);
      });
  }

  return (
    <div className="relative w-full overflow-hidden rounded-lg bg-black">
      <video ref={videoRef} controls={controllable} poster={poster ?? undefined} className="aspect-video w-full" />
      {needsGesture && (
        <button
          type="button"
          onClick={handleManualSync}
          className="absolute inset-0 flex items-center justify-center bg-black/60 text-lg font-semibold text-white"
        >
          ▶ Rejoindre la lecture
        </button>
      )}
      {error && <p className="p-3 text-sm text-accent">{error}</p>}
    </div>
  );
}
