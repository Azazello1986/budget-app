#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
LOG_DIR="logs"
TS=$(date +"%Y%m%d-%H%M%S")
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/smoke-$TS.log"

# безопасные заготовки, чтобы -u не падал
BUD_ID="${BUD_ID:-}"
SM_STEP_ID="${SM_STEP_ID:-}"
STEP2_ID="${STEP2_ID:-}"

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
  BODY=$(cat /tmp/body.$$)
  rm -f /tmp/body.$$
}

# 1) health
req GET /health

# 2) users
SMOKE_EMAIL="${SMOKE_EMAIL:-smoke-$(date +%s)@example.com}"
req POST /users "{\"email\":\"$SMOKE_EMAIL\",\"name\":\"Smoke\"}"
req GET /users

# 3) defaults (можно переопределять окружением)
BUDGET_ID="${BUDGET_ID:-1}"
ACCOUNT_ID="${ACCOUNT_ID:-1}"
ACCOUNT_TO_ID="${ACCOUNT_TO_ID:-2}"
CATEGORY_ID="${CATEGORY_ID:-1}"
STEP_ID="${STEP_ID:-1}"

# 4) budgets
req POST /budgets "{\"name\":\"SMOKE-BUDGET\",\"currency\":\"EUR\",\"owner_user_id\":1}"
# захватываем BUD_ID из ответа
if command -v jq >/dev/null 2>&1; then
  BUD_ID="$(echo "$BODY" | jq -r '.id' 2>/dev/null || true)"
fi
if [ -z "${BUD_ID:-}" ] || [ "$BUD_ID" = "null" ]; then
  BUD_ID="$(curl -s "$API_BASE/budgets" | jq -r '.[0].id' 2>/dev/null || true)"
fi
[ -n "${BUD_ID:-}" ] || { echo "Не удалось получить BUD_ID"; exit 1; }

req GET /budgets

# 5) accounts & categories
req POST /accounts "{\"budget_id\":$BUD_ID,\"name\":\"SMOKE-ACC1\",\"currency\":\"EUR\"}"
req POST /accounts "{\"budget_id\":$BUD_ID,\"name\":\"SMOKE-ACC2\",\"currency\":\"EUR\"}"
req GET /accounts
req POST /categories "{\"budget_id\":$BUD_ID,\"name\":\"SMOKE-CAT\"}"
req GET /categories

# 6) steps (текущий месяц)
YYYYMM=$(date +%Y-%m)
FIRST=$(date -d "$(date +%Y-%m-01)" +%F 2>/dev/null || date -v1d +%F)
LAST=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%F 2>/dev/null || date -v+1m -v-1d +%F)
req POST /steps "{\"budget_id\":$BUD_ID,\"granularity\":\"month\",\"name\":\"SMOKE $YYYYMM\",\"date_start\":\"$FIRST\",\"date_end\":\"$LAST\"}"
# захватываем SM_STEP_ID и STEP2_ID
if command -v jq >/dev/null 2>&1; then
  NEW_STEP_ID="$(echo "$BODY" | jq -r '.id' 2>/dev/null || true)"
fi
SM_STEP_ID="${SM_STEP_ID:-$NEW_STEP_ID}"
STEP2_ID="${STEP2_ID:-$NEW_STEP_ID}"
[ -n "${SM_STEP_ID:-}" ] || SM_STEP_ID="$(curl -s "$API_BASE/steps?budget_id=$BUD_ID" | jq -r '.[0].id' 2>/dev/null || true)"
[ -n "${STEP2_ID:-}" ] || STEP2_ID="$(curl -s "$API_BASE/steps?budget_id=$BUD_ID" | jq -r '.[0].id' 2>/dev/null || true)"

req GET "/steps?budget_id=$BUD_ID"

# 7) operations
req POST /operations "{\"step_id\":$SM_STEP_ID,\"kind\":\"planned\",\"sign\":\"expense\",\"amount\":\"10.00\",\"currency\":\"EUR\",\"account_id\":$ACCOUNT_ID,\"category_id\":$CATEGORY_ID,\"comment\":\"SMOKE planned\"}"
req POST /operations "{\"step_id\":$SM_STEP_ID,\"kind\":\"actual\",\"sign\":\"expense\",\"amount\":\"5.00\",\"currency\":\"EUR\",\"account_id\":$ACCOUNT_ID,\"category_id\":$CATEGORY_ID,\"comment\":\"SMOKE actual\"}"
req POST /operations "{\"step_id\":$SM_STEP_ID,\"kind\":\"actual\",\"sign\":\"transfer\",\"amount\":\"1.00\",\"currency\":\"EUR\",\"account_id\":$ACCOUNT_ID,\"account_id_to\":$ACCOUNT_TO_ID,\"comment\":\"SMOKE transfer\"}"
req GET "/operations?step_id=$SM_STEP_ID"

# --- steps feed/summary/copy_planned ---
req GET "/steps/$SM_STEP_ID/feed"
req GET "/steps/$SM_STEP_ID/summary"

# Копируем плановые из шага 1 в $STEP2_ID
req POST "/steps/1/copy_planned" "{\"to_step_id\":$STEP2_ID}"

echo -e "\nSMOKE END $(date -Is)" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE"