# ── Build stage ──────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline

COPY . .

ARG LIVE_FEED_URL=http://live-feed:8000
ARG NEXT_PUBLIC_LIVE_FEED_URL=http://localhost:8003
ENV LIVE_FEED_URL=${LIVE_FEED_URL}
ENV NEXT_PUBLIC_LIVE_FEED_URL=${NEXT_PUBLIC_LIVE_FEED_URL}

RUN npm run build && mkdir -p /app/public

# ── Production runtime ────────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static     ./.next/static
COPY --from=builder /app/public           ./public

EXPOSE 3000
CMD ["node", "server.js"]
