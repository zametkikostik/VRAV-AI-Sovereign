# Public server checklist

1. DNS A → VPS IP
2. ufw allow 22,80,443 — do not expose 8000/11434
3. `.env`: AUTH_MODE=required, keys set
4. `DOMAIN=… EMAIL=… bash deploy/tls-setup.sh`
5. `docker compose -f docker-compose.prod.yml up -d --build`
6. `scripts/pull-models.sh`
7. `curl -H "X-API-Key: $KEY" https://domain/api/health`
