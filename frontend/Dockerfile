# ── Stage 1: install production dependencies ─────────────────────────────────
# We use `npm ci` (clean install) over `npm install` — it is faster, strictly
# respects package-lock.json, and is idempotent: ideal for CI and image builds.
FROM node:20-alpine AS builder

WORKDIR /build

COPY package*.json ./

RUN npm ci --omit=dev


# ── Stage 2: lean runtime image ──────────────────────────────────────────────
FROM node:20-alpine

# Alpine uses addgroup/adduser, not groupadd/useradd.
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Copy only the production node_modules — no devDependencies in the image.
COPY --from=builder /build/node_modules ./node_modules
COPY app.js .
COPY views ./views

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 3000

# wget is available in node:alpine; it's lighter than curl for a single check.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "app.js"]
