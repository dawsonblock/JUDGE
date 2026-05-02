#!/usr/bin/env bash
set -euo pipefail

# Proof script: Run Alembic migrations against a real Postgres/PostGIS instance
# Usage: ./scripts/proof_postgis.sh
# Requires: Docker available

IMAGE="postgis/postgis:16-3.4"
CONTAINER="judge_postgis_proof"
DB_NAME="judgetracker_proof"
DB_USER="judgetracker"
DB_PASS="judgetracker"
DB_PORT="15432"

cleanup() {
    docker rm -f "$CONTAINER" 2>/dev/null || true
}
trap cleanup EXIT

echo "[proof_postgis] Starting PostGIS container..."
docker run -d \
    --name "$CONTAINER" \
    -e POSTGRES_DB="$DB_NAME" \
    -e POSTGRES_USER="$DB_USER" \
    -e POSTGRES_PASSWORD="$DB_PASS" \
    -p "${DB_PORT}:5432" \
    "$IMAGE"

echo "[proof_postgis] Waiting for Postgres to be ready..."
pg_ready=0
for i in $(seq 1 30); do
    if docker exec "$CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
        echo "[proof_postgis] Postgres ready after ${i}s"
        pg_ready=1
        break
    fi
    sleep 1
done
if [ "$pg_ready" -ne 1 ]; then
    echo "[proof_postgis] ERROR: Postgres did not become ready within 30 seconds" >&2
    docker logs "$CONTAINER" >&2
    exit 1
fi

export DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASS}@localhost:${DB_PORT}/${DB_NAME}"
export JTA_DATABASE_URL="$DATABASE_URL"

echo "[proof_postgis] Running alembic upgrade head..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../backend"
alembic upgrade head

echo "[proof_postgis] Running spatial smoke tests..."
PROOF_LOG="$SCRIPT_DIR/../artifacts/proof/postgis_proof.log"
mkdir -p "$(dirname "$PROOF_LOG")"
python -m pytest app/tests/test_map_bbox.py -v --tb=short 2>&1 | tee "$PROOF_LOG"

echo "[proof_postgis] SUCCESS: Postgres/PostGIS proof passed"
echo "[proof_postgis] Log saved to $PROOF_LOG"
