"use client";

import { useEffect, useRef, useState } from "react";

export default function Dropdown({
  trigger,
  children,
  align = "left",
  showChevron = true,
  triggerClassName,
  panelClassName,
}: {
  trigger: React.ReactNode;
  children: React.ReactNode;
  align?: "left" | "right";
  showChevron?: boolean;
  triggerClassName?: string;
  panelClassName?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={
          triggerClassName ??
          "flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-sm text-muted transition hover:text-foreground"
        }
      >
        {trigger}
        {showChevron && (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        )}
      </button>

      {open && (
        <div
          onClick={() => setOpen(false)}
          className={
            panelClassName ??
            `absolute top-full z-50 mt-2 min-w-44 overflow-hidden rounded-lg border border-white/10 bg-surface py-1.5 shadow-lg ${
              align === "right" ? "right-0" : "left-0"
            }`
          }
        >
          {children}
        </div>
      )}
    </div>
  );
}
