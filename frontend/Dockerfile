FROM node:20-bookworm-slim AS deps

WORKDIR /app

COPY package.json /app/package.json

RUN npm install

FROM node:20-bookworm-slim AS builder

WORKDIR /app

COPY --from=deps /app/node_modules /app/node_modules
COPY . /app

RUN npm run build

FROM node:20-bookworm-slim AS runner

ENV NODE_ENV=production

WORKDIR /app

COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/package.json /app/package.json
COPY --from=builder /app/node_modules /app/node_modules
COPY --from=builder /app/next.config.ts /app/next.config.ts

EXPOSE 3000

CMD ["npm", "run", "start"]
