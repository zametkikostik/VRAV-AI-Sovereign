# Production deploy — VRAV AI

## Docker Compose production

```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d --build
# http://localhost/ via nginx
```

Models:
```bash
docker exec -it vrav-ollama ollama pull llama3.1
docker exec -it vrav-ollama ollama pull nomic-embed-text
```

## Redis rate limit

`REDIS_URL=redis://redis:6379/0` in compose. Without Redis → in-memory bucket.

## Backups

```bash
chmod +x scripts/backup.sh && ./scripts/backup.sh
```

## Secrets

See `deploy/secrets.example.env`. Never commit real `.env`.
Set `AUTH_MODE=required` for public exposure.
