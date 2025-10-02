#!/usr/bin/env bash
set -euo pipefail

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
req GET /budgets

# 5) accounts & categories
req POST /accounts "{\"budget_id\":$BUDGET_ID,\"name\":\"SMOKE-ACC1\",\"currency\":\"EUR\"}"
req POST /accounts "{\"budget_id\":$BUDGET_ID,\"name\":\"SMOKE-ACC2\",\"currency\":\"EUR\"}"
req GET /accounts
req POST /categories "{\"budget_id\":$BUDGET_ID,\"name\":\"SMOKE-CAT\"}"
req GET /categories

# 6) steps (текущий месяц)
YYYYMM=$(date +%Y-%m)
FIRST=$(date -d "$(date +%Y-%m-01)" +%F 2>/dev/null || date -v1d +%F)
LAST=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%F 2>/dev/null || date -v+1m -v-1d +%F)
req POST /steps "{\"budget_id\":$BUDGET_ID,\"granularity\":\"month\",\"name\":\"SMOKE $YYYYMM\",\"date_start\":\"$FIRST\",\"date_end\":\"$LAST\"}"
req GET "/steps?budget_id=$BUDGET_ID"

# 7) operations
req POST /operations "{\"step_id\":$STEP_ID,\"kind\":\"planned\",\"sign\":\"expense\",\"amount\":\"10.00\",\"currency\":\"EUR\",\"account_id\":$ACCOUNT_ID,\"category_id\":$CATEGORY_ID,\"comment\":\"SMOKE planned\"}"
req POST /operations "{\"step_id\":$STEP_ID,\"kind\":\"actual\",\"sign\":\"expense\",\"amount\":\"5.00\",\"currency\":\"EUR\",\"account_id\":$ACCOUNT_ID,\"category_id\":$CATEGORY_ID,\"comment\":\"SMOKE actual\"}"
req POST /operations "{\"step_id\":$STEP_ID,\"kind\":\"actual\",\"sign\":\"transfer\",\"amount\":\"1.00\",\"currency\":\"EUR\",\"account_id\":$ACCOUNT_ID,\"account_id_to\":$ACCOUNT_TO_ID,\"comment\":\"SMOKE transfer\"}"
req GET "/operations?step_id=$STEP_ID"

echo -e "\nSMOKE END $(date -Is)" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE"

# --- steps feed/summary/copy_planned ---

SM_STEP_ID="${SM_STEP_ID:-1}"

echo ">>> GET /steps?budget_id=$BUD_ID"
t=$(date +%s%N)
RESP=$(curl -s -w "\n%{http_code}" "$API_BASE/steps?budget_id=$BUD_ID")
HTTP_CODE=$(echo "$RESP" | tail -n1); BODY=$(echo "$RESP" | sed '$d')
dur $t
log "HTTP_CODE=$HTTP_CODE TIME=$ELAPSED"; log "BODY:\n$BODY"
[ "$HTTP_CODE" = "200" ] || FAIL=1

echo ">>> GET /steps/$SM_STEP_ID/feed"
t=$(date +%s%N)
RESP=$(curl -s -w "\n%{http_code}" "$API_BASE/steps/$SM_STEP_ID/feed")
HTTP_CODE=$(echo "$RESP" | tail -n1); BODY=$(echo "$RESP" | sed '$d')
dur $t
log "HTTP_CODE=$HTTP_CODE TIME=$ELAPSED"; log "BODY:\n$BODY"
[ "$HTTP_CODE" = "200" ] || FAIL=1

echo ">>> GET /steps/$SM_STEP_ID/summary"
t=$(date +%s%N)
RESP=$(curl -s -w "\n%{http_code}" "$API_BASE/steps/$SM_STEP_ID/summary")
HTTP_CODE=$(echo "$RESP" | tail -n1); BODY=$(echo "$RESP" | sed '$d')
dur $t
log "HTTP_CODE=$HTTP_CODE TIME=$ELAPSED"; log "BODY:\n$BODY"
[ "$HTTP_CODE" = "200" ] || FAIL=1

# Копируем плановые из шага 1 в 2 (если шага 2 нет — создадим)
echo ">>> ensure step #2 exists (month current)"
CUR_MONTH=$(date +%Y-%m)
STEP_NAME="SMOKE $CUR_MONTH"
PAYLOAD=$(jq -n \
  --arg bid "$BUD_ID" \
  --arg name "$STEP_NAME" \
  '{budget_id:($bid|tonumber), granularity:"month", name:$name,
    date_start:"'"$(date +%Y-%m-01)"'", date_end:"'"$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%Y-%m-%d)"'"}')

RESP=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/steps" -H "Content-Type: application/json" -d "$PAYLOAD")
HTTP_CODE=$(echo "$RESP" | tail -n1); BODY=$(echo "$RESP" | sed '$d')
if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
  STEP2_ID=$(echo "$BODY" | jq -r '.id')
else
  # попробуем найти уже существующий
  STEP2_ID=$(curl -s "$API_BASE/steps?budget_id=$BUD_ID" | jq -r '.[0].id')
fi

echo ">>> POST /steps/1/copy_planned -> step=$STEP2_ID"
t=$(date +%s%N)
RESP=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/steps/1/copy_planned" \
  -H "Content-Type: application/json" -d "{\"to_step_id\":$STEP2_ID}")
HTTP_CODE=$(echo "$RESP" | tail -n1); BODY=$(echo "$RESP" | sed '$d')
dur $t
log "HTTP_CODE=$HTTP_CODE TIME=$ELAPSED"; log "BODY:\n$BODY"
[ "$HTTP_CODE" = "200" ] || FAIL=1
