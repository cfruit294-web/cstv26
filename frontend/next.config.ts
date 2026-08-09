import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "m.media-amazon.com",
      },
      {
        protocol: "http",
        hostname: "127.0.0.1",
        port: "8000",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
      },
      {
        // En docker-compose (prod), nginx sert l'API sur le port 80 (pas de :8000).
        protocol: "http",
        hostname: "localhost",
      },
    ],
  },
};

export default nextConfig;
