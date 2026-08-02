# VRAV AI — common targets
.PHONY: install run index eval test smoke docker-prod backup pull-models quickstart

install:
	python -m pip install -r requirements.txt
	python -m pip install pytest pytest-asyncio httpx

run:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

index:
	PYTHONPATH=. python scripts/index_docs.py

eval:
	PYTHONPATH=. python evals/offline_rag_eval.py

test:
	pytest tests/ -q \
	  --ignore=tests/test_e2e_ollama.py \
	  --ignore=tests/test_eurlex.py \
	  --ignore=tests/test_cellar.py

smoke:
	bash scripts/smoke.sh

docker-prod:
	docker compose -f docker-compose.prod.yml up -d --build

backup:
	bash scripts/backup.sh

pull-models:
	ollama pull llama3.1
	ollama pull nomic-embed-text

quickstart: install pull-models index
	@echo "Start: make run  →  http://127.0.0.1:8000"
