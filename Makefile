.PHONY: backend-install backend-test frontend-install frontend-check verify docker-smoke

PYTHON := python3.11

backend-install:
	cd backend && $(PYTHON) -m pip install -e ".[test]"

backend-test:
	cd backend && $(PYTHON) -m compileall -q app
	cd backend && $(PYTHON) -m pytest -q

frontend-install:
	cd frontend && npm ci

frontend-check:
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm run build

verify: backend-install backend-test frontend-install frontend-check

docker-smoke:
	docker compose up -d --build
	curl -f http://localhost:8000/docs >/dev/null
	curl -f http://localhost:3000 >/dev/null
	docker compose down -v
