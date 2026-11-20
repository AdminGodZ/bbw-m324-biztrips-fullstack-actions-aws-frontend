# syntax=docker/dockerfile:1.7
# Multi-stage build: Vite production build (Node) -> static files behind nginx.
FROM node:24-alpine AS build
WORKDIR /build
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY . .
# Backend service URL (ECS: ALB URL from the GitHub variable VITE_API_BASE_URL, Compose: "/").
ARG VITE_API_BASE_URL=/
ARG APP_VERSION=dev
ARG GIT_SHA=local
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_APP_VERSION=${APP_VERSION}
RUN npm run build \
 && printf '{"name":"biztrips-frontend","version":"%s","commit":"%s","apiBaseUrl":"%s"}\n' \
      "$APP_VERSION" "$GIT_SHA" "$VITE_API_BASE_URL" > dist/version.json

FROM nginx:stable-alpine
ARG APP_VERSION=dev
ARG GIT_SHA=local
LABEL org.opencontainers.image.title="biztrips-frontend" \
      org.opencontainers.image.description="M324 RefCard05 Business Trips frontend (React + Vite on nginx)" \
      org.opencontainers.image.authors="Tim Held" \
      org.opencontainers.image.source="https://github.com/AdminGodZ/bbw-m324-biztrips-fullstack-actions-aws-frontend" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}"
# Only used by the /v1 and /actuator proxy (Docker Compose); on ECS the browser calls the ALB directly.
ENV BACKEND_ORIGIN=http://backend:8080 \
    NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --chmod=755 docker/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
COPY --from=build /build/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1/health || exit 1
