# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app

# Dependencies layer, cached separately from source changes
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# --- Runtime stage: static build served via nginx ---
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD wget -qO- http://127.0.0.1:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]

# --- Local dev alternative ---
# For hot-reload during development, don't use this image at all —
# point docker-compose at a separate dev target instead, e.g.:
#
# FROM node:20-alpine AS dev
# WORKDIR /app
# COPY package.json package-lock.json* ./
# RUN npm ci
# COPY . .
# EXPOSE 5173
# CMD ["npm", "run", "dev", "--", "--host"]
