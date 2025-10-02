#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
LOG_DIR="logs"
TS=$(date +"%Y%m%d-%H%M%S")
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/smoke-$TS.log"

# Требуем jq для разбора ID
if ! command -v jq >/dev/null 2>&1; then
  echo "jq не найден. Установи: sudo apt install -y jq" | tee -a "$LOG_FILE"
  exit 1
fi

echo "SMOKE START $(date -Is)" | tee -a "$LOG_FILE"
echo "API_BASE=$API_BASE" | tee -a "$LOG_FILE"

# Глобальные переменные, BODY заполняется в req()
BODY=""

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
  BODY="$(cat /tmp/body.$$)"
  rm -f /tmp/body.$$
}

# 1) health
req GET /health

# 2) users
SMOKE_EMAIL="${SMOKE_EMAIL:-smoke-$(date +%s)@example.com}"
req POST /users "{\"email\":\"$SMOKE_EMAIL\",\"name\":\"Smoke\"}"
req GET /users

# 3) бюджет — создаём новый и берём его id
req POST /budgets '{"name":"SMOKE-BUDGET","currency":"EUR","owner_user_id":1}'
BUD_ID="$(echo "$BODY" | jq -r '.id')"
if [[ -z "$BUD_ID" || "$BUD_ID" == "null" ]]; then
  echo "Не удалось получить id бюджета" | tee -a "$LOG_FILE"; exit 1
fi
req GET /budgets

# 4) аккаунты в том же бюджете
req POST /accounts "{\"budget_id\":$BUD_ID,\"name\":\"SMOKE-ACC1\",\"currency\":\"EUR\"}"
ACC1_ID="$(echo "$BODY" | jq -r '.id')"
req POST /accounts "{\"budget_id\":$BUD_ID,\"name\":\"SMOKE-ACC2\",\"currency\":\"EUR\"}"
ACC2_ID="$(echo "$BODY" | jq -r '.id')"
req GET /accounts

# 5) категория в том же бюджете
req POST /categories "{\"budget_id\":$BUD_ID,\"name\":\"SMOKE-CAT\"}"
CAT_ID="$(echo "$BODY" | jq -r '.id')"
req GET /categories

# 6) шаги (два шага в одном бюджете)
YYYYMM=$(date +%Y-%m)
FIRST=$(date -d "$(date +%Y-%m-01)" +%F 2>/dev/null || date -v1d +%F)
LAST=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%F 2>/dev/null || date -v+1m -v-1d +%F)

# Первый шаг (основной для операций)
req POST /steps "{\"budget_id\":$BUD_ID,\"granularity\":\"month\",\"name\":\"SMOKE $YYYYMM\",\"date_start\":\"$FIRST\",\"date_end\":\"$LAST\"}"
STEP1_ID="$(echo "$BODY" | jq -r '.id')"

# Второй шаг для copy_planned (если захочешь смотреть перенос)
req POST /steps "{\"budget_id\":$BUD_ID,\"granularity\":\"month\",\"name\":\"SMOKE $YYYYMM COPY\",\"date_start\":\"$FIRST\",\"date_end\":\"$LAST\"}"
STEP2_ID="$(echo "$BODY" | jq -r '.id')"

req GET "/steps?budget_id=$BUD_ID"

# 7) операции в рамках одного бюджета/шага
req POST /operations "{\"step_id\":$STEP1_ID,\"kind\":\"planned\",\"sign\":\"expense\",\"amount\":\"10.00\",\"currency\":\"EUR\",\"account_id\":$ACC1_ID,\"category_id\":$CAT_ID,\"comment\":\"SMOKE planned\"}"
req POST /operations "{\"step_id\":$STEP1_ID,\"kind\":\"actual\",\"sign\":\"expense\",\"amount\":\"5.00\",\"currency\":\"EUR\",\"account_id\":$ACC1_ID,\"category_id\":$CAT_ID,\"comment\":\"SMOKE actual\"}"
req POST /operations "{\"step_id\":$STEP1_ID,\"kind\":\"actual\",\"sign\":\"transfer\",\"amount\":\"1.00\",\"currency\":\"EUR\",\"account_id\":$ACC1_ID,\"account_id_to\":$ACC2_ID,\"comment\":\"SMOKE transfer\"}"
req GET "/operations?step_id=$STEP1_ID"

# 8) лента/сводка шага
req GET "/steps/$STEP1_ID/feed"
req GET "/steps/$STEP1_ID/summary"

# 9) копирование плановых из STEP1 -> STEP2 (один и тот же бюджет)
req POST "/steps/$STEP1_ID/copy_planned" "{\"to_step_id\":$STEP2_ID}"
req GET "/operations?step_id=$STEP2_ID"

echo -e "\nSMOKE END $(date -Is)" | tee -a "$LOG_FILE"
echo "Log saved to: $LOG_FILE"