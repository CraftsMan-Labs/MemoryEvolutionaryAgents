FROM oven/bun:1.1

WORKDIR /app

COPY dashboard/package.json ./package.json
COPY dashboard/tsconfig.json ./tsconfig.json
COPY dashboard/vite.config.ts ./vite.config.ts
COPY dashboard/index.html ./index.html
COPY dashboard/src ./src

RUN bun install

EXPOSE 5173

CMD ["bun", "run", "dev"]
