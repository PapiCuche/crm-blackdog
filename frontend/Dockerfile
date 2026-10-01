# syntax=docker/dockerfile:1
# Frontend (Next.js standalone). Versiones de ADR-012 §4.1: Node 24.21.0, pnpm 12.8.1.
FROM node:24.21.0-bookworm-slim AS build
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install --global --no-audit --no-fund pnpm@12.8.1
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# Los rewrites de Next se fijan en el build; en el stack los enruta Caddy (same-origin).
ARG BACKEND_ORIGIN=http://backend:8000
RUN BACKEND_ORIGIN="$BACKEND_ORIGIN" pnpm build

FROM node:24.21.0-bookworm-slim AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/').then(r => process.exit(r.ok ? 0 : 1), () => process.exit(1))"]
CMD ["node", "server.js"]
