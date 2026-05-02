#!/usr/bin/env bash
set -euo pipefail

# Judge Atlas - Final acceptance proof
# Usage: ./scripts/proof_all.sh
# Outputs: artifacts/proof/final_proof.log, artifacts/proof/final_manifest.json

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
PROOF_DIR="$REPO_ROOT/artifacts/proof"
mkdir -p "$PROOF_DIR"
LOG="$PROOF_DIR/final_proof.log"
MANIFEST="$PROOF_DIR/final_manifest.json"

GIT_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")"
PYTHON_VERSION="$(python3 --version 2>/dev/null || echo "unknown")"
NODE_VERSION="$(node --version 2>/dev/null || echo "unknown")"
OS="$(uname -s)"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

PASS=0
FAIL=0
SKIP=0
FAILURES=()

run_step() {
    local name="$1"
    local cmd="$2"
    echo "=== $name ===" | tee -a "$LOG"
    if eval "$cmd" >> "$LOG" 2>&1; then
        echo "PASS: $name" | tee -a "$LOG"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name" | tee -a "$LOG"
        FAIL=$((FAIL + 1))
        FAILURES+=("$name")
    fi
}

cd "$REPO_ROOT"

run_step "backend_compile" "python3 -m py_compile backend/app/main.py"
run_step "backend_tests" "cd backend && python -m pytest app/tests/ -v --tb=short -q"
run_step "alembic_sqlite" "cd backend && DATABASE_URL=sqlite:///./proof_test.db alembic upgrade head && rm -f proof_test.db"
run_step "frontend_lint" "cd frontend && npm run lint"
run_step "frontend_build" "cd frontend && npm run build"

if command -v docker &>/dev/null; then
    run_step "docker_compose_proof" "bash scripts/proof_docker_compose.sh"
else
    echo "SKIP: docker_compose_proof (Docker not available)" | tee -a "$LOG"
    SKIP=$((SKIP + 1))
fi

# Build failures JSON array
FAILURES_JSON="["
for i in "${!FAILURES[@]}"; do
    if [ $i -gt 0 ]; then FAILURES_JSON+=","; fi
    FAILURES_JSON+="\"${FAILURES[$i]}\""
done
FAILURES_JSON+="]"

cat > "$MANIFEST" <<EOF
{
  "git_commit": "$GIT_COMMIT",
  "python_version": "$PYTHON_VERSION",
  "node_version": "$NODE_VERSION",
  "os": "$OS",
  "timestamp": "$TIMESTAMP",
  "pass": $PASS,
  "fail": $FAIL,
  "skip": $SKIP,
  "failures": $FAILURES_JSON,
  "release_status": "alpha"
}
EOF

echo "" | tee -a "$LOG"
echo "=== FINAL SUMMARY ===" | tee -a "$LOG"
echo "PASS: $PASS | FAIL: $FAIL | SKIP: $SKIP" | tee -a "$LOG"
echo "Release status: ALPHA (not production-ready)" | tee -a "$LOG"
echo "Manifest: $MANIFEST" | tee -a "$LOG"
echo "Log: $LOG" | tee -a "$LOG"

[ $FAIL -eq 0 ] && exit 0 || exit 1
