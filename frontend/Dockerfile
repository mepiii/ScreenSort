# Purpose: Build and serve ScreenSort frontend container image.
# Callers: docker compose and manual docker builds.
# Deps: Node, npm, nginx, frontend project files.
# API: nginx on port 80.
# Side effects: installs npm dependencies during image build.
FROM node:24-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV VITE_API_BASE_URL=/api
RUN npm run build

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
