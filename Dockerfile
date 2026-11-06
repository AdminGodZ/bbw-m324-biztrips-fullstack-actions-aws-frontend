FROM node:24-alpine AS build
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build
FROM nginx:stable-alpine
ENV BACKEND_ORIGIN=http://backend:8080
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /build/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1/health || exit 1
