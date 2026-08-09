import { PUBLIC_API_URL } from "@/lib/config";

export function resolveMediaUrl(path: string | null | undefined) {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${PUBLIC_API_URL}/media/${path.replace(/^\/?media\//, "")}`;
}
