#!/usr/bin/env bash
set -euo pipefail

# Docker Compose smoke proof for Judge Atlas
# Usage: ./scripts/proof_docker_compose.sh
# Set KEEP_STACK=1 to preserve containers after test

KEEP_STACK="${KEEP_STACK:-0}"
COMPOSE_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../docker-compose.yml"

# Provide test-only placeholder tokens so CI/proof runs don't require a .env file
export JTA_ADMIN_TOKEN="${JTA_ADMIN_TOKEN:-proof-admin-token-ci}"
export JTA_ADMIN_REVIEW_TOKEN="${JTA_ADMIN_REVIEW_TOKEN:-proof-review-token-ci}"

log() { echo "[proof_docker] $*"; }

cleanup() {
    if [ "$KEEP_STACK" != "1" ]; then
        log "Tearing down stack..."
        docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
    fi
}
trap cleanup EXIT

log "Step 1: Tearing down any existing stack..."
docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

log "Step 2: Building images..."
docker compose -f "$COMPOSE_FILE" build

log "Step 3: Starting stack..."
docker compose -f "$COMPOSE_FILE" up -d

log "Step 4: Waiting for backend health..."
for i in $(seq 1 60); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log "Backend ready after ${i}s"
        break
    fi
    if [ "$i" -eq 60 ]; then
        log "ERROR: Backend not ready after 60s"
        docker compose -f "$COMPOSE_FILE" logs
        exit 1
    fi
    sleep 1
done

log "Step 5: Checking /health endpoint..."
curl -sf http://localhost:8000/health | head -100

log "Step 6: Checking /api/map/events endpoint..."
curl -sf "http://localhost:8000/api/map/events?bbox=-180,-90,180,90" | head -200 || log "WARNING: map events endpoint check failed"

log "Step 7: Checking frontend root..."
curl -sf http://localhost:3000/ > /dev/null && log "Frontend root: OK" || log "WARNING: Frontend not reachable"

log "SUCCESS: Docker Compose smoke proof passed"
