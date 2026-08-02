# Production deploy

## systemd
Copy `vrav.service` to `/etc/systemd/system/`, set `/opt/vrav/.env`, enable service.

## nginx
Use `nginx.conf` + certbot for TLS and SSE (`proxy_buffering off`).

## Kubernetes
`kubectl apply -f deploy/k8s/deployment.yaml` (edit host + secrets).

## Ollama legal alias
`ollama create bggpt-legal -f deploy/Modelfile.bggpt-legal`
