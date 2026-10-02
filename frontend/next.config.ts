import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// Topología same-origin (ADR-003 §1): el navegador solo habla con este origen. En local, Next
// hace de proxy de /api y /ws hacia Django; en el stack de compose lo hace Caddy (mismas rutas).
const backend = (process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  poweredByHeader: false,
  output: "standalone", // imagen mínima (frontend/Dockerfile)
  reactStrictMode: true,
  skipTrailingSlashRedirect: true, // Django usa barra final: /api/…/ pasa intacto al backend
  async rewrites() {
    return [
      { source: "/api/:path*/", destination: `${backend}/api/:path*/` }, // conserva la barra
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/ws/:path*/", destination: `${backend}/ws/:path*/` }, // rutas de Channels: /…/
      { source: "/ws/:path*", destination: `${backend}/ws/:path*` },
    ];
  },
  async headers() {
    // Cabeceras fijas. La CSP lleva un nonce por petición y la emite src/proxy.ts (F2-07).
    // HSTS: el navegador lo ignora sobre HTTP (stack local) y lo aplica tras el proxy con TLS.
    const base = [
      { key: "X-Frame-Options", value: "DENY" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains; preload" },
      { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
      { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(), payment=()" },
    ];
    return [{ source: "/:path*", headers: base }];
  },
};

export default createNextIntlPlugin("./src/i18n/request.ts")(nextConfig);
