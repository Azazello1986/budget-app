#!/usr/bin/env bash

set -euo pipefail

run_smoke() {
  API_BASE="${API_BASE:-http://127.0.0.1:8000}"
  LOG_DIR="logs"
  TS=$(date +"%Y%m%d-%H%M%S")
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/smoke-$TS.log"

  echo "SMOKE START $(date -Is)" | tee -a "$LOG_FILE"
  echo "API_BASE=$API_BASE" | tee -a "$LOG_FILE"

  req() {
    local method="$1"; shift
    local path="$1"; shift
    local data="${1:-}"
    echo -e "\n>>> ${method} ${path}" | tee -a "$LOG_FILE"
    if [[ -n "$data" ]]; then
      curl -sS -o /tmp/body.$$ -w 'HTTP_CODE=%{http_code} TIME=%{time_total}\n' \
        -H 'Content-Type: application/json' -X "$method" "$API_BASE$path" -d "$data" \
        | tee -a "$LOG_FILE"
    else
      curl -sS -o /tmp/body.$$ -w 'HTTP_CODE=%{http_code} TIME=%{time_total}\n' \
        -X "$method" "$API_BASE$path" \
        | tee -a "$LOG_FILE"
    fi
    echo "BODY:" | tee -a "$LOG_FILE"
    cat /tmp/body.$$ | tee -a "$LOG_FILE"
    rm -f /tmp/body.$$
  }

  # 1) health
  req GET /health

  # 2) users: try create (idempotent-ish) and list
  SMOKE_EMAIL="${SMOKE_EMAIL:-smoke-$(date +%s)@example.com}"
  req POST /users "{\"email\":\"$SMOKE_EMAIL\",\"name\":\"Smoke\"}"
  req GET /users

  # 3) budgets/accounts/categories/steps — assume budget_id=1 exists in this MRV
  BUDGET_ID="${BUDGET_ID:-1}"
  ACCOUNT_ID="${ACCOUNT_ID:-1}"
  ACCOUNT_TO_ID="${ACCOUNT_TO_ID:-2}"
  CATEGORY_ID="${CATEGORY_ID:-1}"
  STEP_ID="${STEP_ID:-1}"

  # create budget (may already exist)
  req POST /budgets "{\"name\":\"SMOKE-BUDGET\",\"currency\":\"EUR\",\"owner_user_id\":1}"

  # list budgets
  req GET /budgets

  # 4) accounts & categories (may already exist)
  req POST /accounts "{\"budget_id\":$BUDGET_ID,\"name\":\"SMOKE-ACC1\",\"currency\":\"EUR\"}"
  req POST /accounts "{\"budget_id\":$BUDGET_ID,\"name\":\"SMOKE-ACC2\",\"currency\":\"EUR\"}"
  req GET /accounts

  req POST /categories "{\"budget_id\":$BUDGET_ID,\"name\":\"SMOKE-CAT\"}"
  req GET /categories

  # 5) steps (create one for current month if needed and list)
  YYYYMM=$(date +%Y-%m)
  FIRST=$(date -d "$(date +%Y-%m-01)" +%F 2>/dev/null || date -v1d +%F)
  LAST=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%F 2>/dev/null || date -v+1m -v-1d +%F)
  req POST /steps "{\"budget_id\":$BUDGET_ID,\"granularity\":\"month\",\"name\":\"SMOKE $YYYYMM\",\"date_start\":\"$FIRST\",\"date_end\":\"$LAST\"}"
  req GET "/steps?budget_id=$BUDGET_ID"

  # 6) operations: planned expense, actual expense, transfer (ids are assumed for MRV)
  req POST /operations "{\"step_id\":$STEP_ID,\"kind\":\"planned\",\"sign\":\"expense\",\"amount\":\"10.00\",\"currency\":\"EUR\",\"account_id\":$ACCOUNT_ID,\"category_id\":$CATEGORY_ID,\"comment\":\"SMOKE planned\"}"
  req POST /operations "{\"step_id\":$STEP_ID,\"kind\":\"actual\",\"sign\":\"expense\",\"amount\":\"5.00\",\"currency\":\"EUR\",\"account_id\":$ACCOUNT_ID,\"category_id\":$CATEGORY_ID,\"comment\":\"SMOKE actual\"}"
  req POST /operations "{\"step_id\":$STEP_ID,\"kind\":\"actual\",\"sign\":\"transfer\",\"amount\":\"1.00\",\"currency\":\"EUR\",\"account_id\":$ACCOUNT_ID,\"account_id_to\":$ACCOUNT_TO_ID,\"comment\":\"SMOKE transfer\"}"
  req GET "/operations?step_id=$STEP_ID"

  echo -e "\nSMOKE END $(date -Is)" | tee -a "$LOG_FILE"
  echo "Log saved to: $LOG_FILE"
}

# If called as `./scripts/deploy.sh smoke` or `./scripts/deploy.sh test`, run smoke and exit
if [[ "${1:-}" == "smoke" || "${1:-}" == "test" ]]; then
  run_smoke
  exit 0
fi

# (existing deploy logic below this line remains unchanged)