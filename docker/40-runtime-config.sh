#!/bin/sh
# Optional runtime override of the backend URL, e.g. API_BASE_URL=/ in Docker Compose so that the same
# image that runs on ECS (built with VITE_API_BASE_URL=<ALB URL>) talks to the local backend instead.
set -eu
if [ -n "${API_BASE_URL:-}" ]; then
  if ! printf '%s' "$API_BASE_URL" | grep -Eq '^(/|https?://[A-Za-z0-9.:-]+/?)$'; then
    echo "40-runtime-config: invalid API_BASE_URL '$API_BASE_URL' (expected / or http(s)://host[:port])" >&2
    exit 1
  fi
  printf 'window.__BIZTRIPS_CONFIG__ = {"apiBaseUrl": "%s"};\n' "$API_BASE_URL" > /usr/share/nginx/html/config.js
  echo "40-runtime-config: API base URL overridden with $API_BASE_URL"
fi
