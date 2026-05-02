#!/bin/bash
set -euo pipefail

# colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ARTIFACTS_DIR="${SCRIPT_DIR}/../artifacts/proof"
mkdir -p "${ARTIFACTS_DIR}"

LOG_FILE="${ARTIFACTS_DIR}/final_proof.log"
MANIFEST_FILE="${ARTIFACTS_DIR}/final_manifest.json"

# Output functions
run_step() {
    local step_name=$1
    local step_cmd=$2
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running: $step_name"
    echo "Command: $step_cmd"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if eval "$step_cmd" 2>&1 | tee -a "${LOG_FILE}"; then
        echo -e "${GREEN}✓ $step_name passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $step_name failed${NC}"
        return 1
    fi
}

# Clear previous logs
> "${LOG_FILE}"

echo "Starting proof of all systems at $(date)" | tee -a "${LOG_FILE}"

# Track which steps passed
passed_steps=()
failed_steps=()

# Backend setup and tests
run_step "backend_install" "cd backend && python -m pip install -e '.[test]' -q" && \
    passed_steps+=("backend_install") || failed_steps+=("backend_install")

run_step "backend_compile" "cd backend && python -m compileall -q app" && \
    passed_steps+=("backend_compile") || failed_steps+=("backend_compile")

run_step "backend_tests" "cd backend && python -m pytest -q" && \
    passed_steps+=("backend_tests") || failed_steps+=("backend_tests")

# Frontend setup and checks
run_step "frontend_install" "cd frontend && npm ci 2>&1 | grep -v 'npm warn' || true" && \
    passed_steps+=("frontend_install") || failed_steps+=("frontend_install")

run_step "frontend_lint" "cd frontend && npm run lint" && \
    passed_steps+=("frontend_lint") || failed_steps+=("frontend_lint")

run_step "frontend_typecheck" "cd frontend && npm run typecheck" && \
    passed_steps+=("frontend_typecheck") || failed_steps+=("frontend_typecheck")

run_step "frontend_build" "cd frontend && npm run build" && \
    passed_steps+=("frontend_build") || failed_steps+=("frontend_build")

# Write manifest
cat > "${MANIFEST_FILE}" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "passed_steps": [$(printf '%s\n' "${passed_steps[@]}" | sed 's/^/"/;s/$/"/' | paste -sd ',' -)],
  "failed_steps": [$(printf '%s\n' "${failed_steps[@]}" | sed 's/^/"/;s/$/"/' | paste -sd ',' -)],
  "total_passed": ${#passed_steps[@]},
  "total_failed": ${#failed_steps[@]},
  "log_file": "${LOG_FILE}"
}
EOF

echo "" | tee -a "${LOG_FILE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "${LOG_FILE}"
echo "Proof Summary:" | tee -a "${LOG_FILE}"
echo -e "${GREEN}Passed: ${#passed_steps[@]}${NC}" | tee -a "${LOG_FILE}"
echo -e "${RED}Failed: ${#failed_steps[@]}${NC}" | tee -a "${LOG_FILE}"
echo "Log: ${LOG_FILE}" | tee -a "${LOG_FILE}"
echo "Manifest: ${MANIFEST_FILE}" | tee -a "${LOG_FILE}"

if [ ${#failed_steps[@]} -gt 0 ]; then
    echo "" | tee -a "${LOG_FILE}"
    echo -e "${RED}Failed steps:${NC}" | tee -a "${LOG_FILE}"
    for step in "${failed_steps[@]}"; do
        echo -e "  - $step" | tee -a "${LOG_FILE}"
    done
    exit 1
fi

echo -e "${GREEN}All proof steps passed!${NC}" | tee -a "${LOG_FILE}"
exit 0
