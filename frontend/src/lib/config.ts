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

export const WS_BASE_URL = PUBLIC_API_URL.replace(/^http/, "ws");
