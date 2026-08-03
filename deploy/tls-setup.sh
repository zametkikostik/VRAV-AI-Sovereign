#!/usr/bin/env bash
# DOMAIN=vrav.example.com EMAIL=admin@example.com bash deploy/tls-setup.sh
set -euo pipefail
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
MODE="${MODE:-host}"
if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Set DOMAIN and EMAIL"
  exit 1
fi
if [[ "$MODE" == "host" ]]; then
  CONF_SRC="$(cd "$(dirname "$0")" && pwd)/nginx.conf"
  sudo cp "$CONF_SRC" /etc/nginx/sites-available/vrav
  sudo sed -i "s/vrav.example.com/${DOMAIN}/g" /etc/nginx/sites-available/vrav
  sudo ln -sf /etc/nginx/sites-available/vrav /etc/nginx/sites-enabled/vrav
  sudo nginx -t && sudo systemctl reload nginx
  sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
else
  mkdir -p "$(cd "$(dirname "$0")" && pwd)/certs"
  docker run --rm -it -v "$(cd "$(dirname "$0")" && pwd)/certs:/etc/letsencrypt" -p 80:80 \
    certbot/certbot certonly --standalone -d "$DOMAIN" --agree-tos -m "$EMAIL" --non-interactive
fi
echo "Set AUTH_MODE=required and restart. Do not expose 8000/11434."
