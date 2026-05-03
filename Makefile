.PHONY: backend-install backend-test frontend-install frontend-check verify docker-smoke proof

backend-install:
	cd backend && python -m pip install -e ".[test]"

backend-test:
	cd backend && python -m compileall -q app
	cd backend && python -m pytest -q

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

proof:
	@mkdir -p artifacts/proof
	@TIMESTAMP=$$(date +%Y%m%d-%H%M%S); \
	echo "=== Backend tests $(TIMESTAMP) ===" | tee artifacts/proof/backend-$${TIMESTAMP}.log; \
	cd backend && python -m compileall -q app 2>&1 | tee -a ../artifacts/proof/backend-$${TIMESTAMP}.log; \
	python -m pytest -q 2>&1 | tee -a ../artifacts/proof/backend-$${TIMESTAMP}.log; \
	echo "=== Frontend checks $(TIMESTAMP) ===" | tee ../artifacts/proof/frontend-$${TIMESTAMP}.log; \
	cd ../frontend && npm run lint 2>&1 | tee -a ../artifacts/proof/frontend-$${TIMESTAMP}.log; \
	npm run typecheck 2>&1 | tee -a ../artifacts/proof/frontend-$${TIMESTAMP}.log; \
	npm run build 2>&1 | tee -a ../artifacts/proof/frontend-$${TIMESTAMP}.log; \
	echo "Proof logs saved to artifacts/proof/backend-$${TIMESTAMP}.log and artifacts/proof/frontend-$${TIMESTAMP}.log"
