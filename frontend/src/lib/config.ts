// URL publique de l'API : celle que le navigateur utilise (images, WebSocket), donc jamais un nom
// d'hôte interne à Docker (ex: "web") — le navigateur ne pourrait pas le résoudre.
export const PUBLIC_API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

// URL utilisée pour les appels serveur (server components, route handlers) : en docker-compose, le
// conteneur frontend ne peut pas s'appeler lui-même via le domaine public (nginx), il doit passer
// par le réseau interne (INTERNAL_API_URL=http://web:8000). Sans docker (npm run dev), il n'y a pas
// de conteneur donc on retombe sur PUBLIC_API_URL.
export const API_BASE_URL =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_URL?.replace(/\/$/, "") ?? PUBLIC_API_URL
    : PUBLIC_API_URL;

// En-têtes à joindre aux appels serveur passant par le réseau interne. Django (settings prod) ne
// connaît pas l'hôte "web" et redirige le HTTP vers HTTPS : on lui annonce donc l'hôte et le
// protocole PUBLICS, comme le ferait nginx. Ça garde aussi les URLs absolues qu'il génère
// (miniatures, avatars...) correctes pour le navigateur. Vide hors docker (pas d'appel interne).
function internalForwardedHeaders(): Record<string, string> {
  if (typeof window !== "undefined" || !process.env.INTERNAL_API_URL) return {};
  const publicUrl = new URL(PUBLIC_API_URL);
  return {
    "X-Forwarded-Host": publicUrl.host,
    "X-Forwarded-Proto": publicUrl.protocol.replace(":", ""),
  };
}

export const SERVER_FORWARDED_HEADERS = internalForwardedHeaders();

export const WS_BASE_URL = PUBLIC_API_URL.replace(/^http/, "ws");
