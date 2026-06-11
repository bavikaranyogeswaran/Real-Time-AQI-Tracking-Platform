#!/usr/bin/env bash
# smoke_test.sh — end-to-end smoke test against the running Docker stack.
#
# Usage:
#   bash scripts/smoke_test.sh
#
# Requires: curl, jq, docker
# Exits 0 on all-pass, 1 on any failure.

set -euo pipefail

API="http://localhost:8000"
FRONTEND="http://localhost:5173"
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}PASS${NC}  $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}FAIL${NC}  $1"; FAIL=$((FAIL + 1)); }
section() { echo -e "\n${YELLOW}▸ $1${NC}"; }

# ---------------------------------------------------------------------------
# 1. Container health
# ---------------------------------------------------------------------------
section "Container health"

for svc in aqi_backend aqi_db aqi_frontend; do
  status=$(docker inspect --format='{{.State.Status}}' "$svc" 2>/dev/null || echo "missing")
  if [[ "$status" == "running" ]]; then
    pass "Container $svc is running"
  else
    fail "Container $svc — status: $status"
  fi
done

# ---------------------------------------------------------------------------
# Helper: assert HTTP status and optionally a jq expression
# ---------------------------------------------------------------------------
check() {
  local label="$1"
  local url="$2"
  local expected_status="${3:-200}"
  local jq_check="${4:-}"

  http_code=$(curl -s -o /tmp/smoke_body -w "%{http_code}" "$url")
  body=$(cat /tmp/smoke_body)

  if [[ "$http_code" != "$expected_status" ]]; then
    fail "$label — expected HTTP $expected_status, got $http_code"
    return
  fi

  if [[ -n "$jq_check" ]]; then
    result=$(echo "$body" | jq -e "$jq_check" 2>/dev/null || echo "false")
    if [[ "$result" == "false" || "$result" == "null" ]]; then
      fail "$label — jq check failed: $jq_check (body: ${body:0:120})"
      return
    fi
  fi

  pass "$label"
}

# ---------------------------------------------------------------------------
# 2. Health check
# ---------------------------------------------------------------------------
section "Health check"
check "GET /health — status ok" "$API/health" 200 '.status == "ok"'

# ---------------------------------------------------------------------------
# 3. Pick a city from the live database for subsequent tests
# ---------------------------------------------------------------------------
section "Locations"
check "GET /api/locations — 200, non-empty list" "$API/api/locations" 200 '. | length > 0'

CITY=$(curl -s "$API/api/locations" | jq -r '.[0].city')
if [[ -z "$CITY" || "$CITY" == "null" ]]; then
  echo -e "  ${RED}ABORT${NC}  No cities in database — cannot continue endpoint tests."
  echo -e "\n${RED}Smoke test aborted — seed some location data first.${NC}"
  exit 1
fi
echo "  Using city: $CITY"

# ---------------------------------------------------------------------------
# 4. AQI endpoints
# ---------------------------------------------------------------------------
section "AQI endpoints (city=$CITY)"
check "GET /api/aqi/current        — 200, has aqi field"   "$API/api/aqi/current?city=$CITY"        200 '.aqi | numbers'
check "GET /api/aqi/current        — 404 for unknown city" "$API/api/aqi/current?city=NoSuchXYZ"    404
check "GET /api/aqi/history        — 200, list"            "$API/api/aqi/history?city=$CITY"        200 '. | type == "array"'
check "GET /api/aqi/history days=1 — 200, list"            "$API/api/aqi/history?city=$CITY&days=1" 200 '. | type == "array"'
check "GET /api/aqi/history days=0 — 422 validation"       "$API/api/aqi/history?city=$CITY&days=0" 422
check "GET /api/aqi/pollutants     — 200, has pm25"        "$API/api/aqi/pollutants?city=$CITY"     200 '.pm25 | numbers'
check "GET /api/aqi/forecast       — 200, list"            "$API/api/aqi/forecast?city=$CITY"       200 '. | type == "array"'

# ---------------------------------------------------------------------------
# 5. Alert endpoints
# ---------------------------------------------------------------------------
section "Alert endpoints"
check "GET /api/alerts             — 200, list" "$API/api/alerts" 200 '. | type == "array"'

LOC_ID=$(curl -s "$API/api/locations" | jq -r --arg c "$CITY" '.[] | select(.city==$c) | .location_id')
RULE_PAYLOAD="{\"location_id\":\"$LOC_ID\",\"alert_type\":\"smoke_test_rule\",\"threshold_value\":999}"
RULE_RESP=$(curl -s -X POST -H "Content-Type: application/json" -d "$RULE_PAYLOAD" -w "\n%{http_code}" "$API/api/alerts/rules")
RULE_CODE=$(echo "$RULE_RESP" | tail -1)
RULE_BODY=$(echo "$RULE_RESP" | head -1)

if [[ "$RULE_CODE" == "201" ]]; then
  pass "POST /api/alerts/rules     — 201, rule created"
else
  fail "POST /api/alerts/rules     — expected 201, got $RULE_CODE"
fi

# Clean up the smoke-test rule right away
RULE_ID=$(echo "$RULE_BODY" | jq -r '.rule_id // empty')
if [[ -n "$RULE_ID" ]]; then
  docker exec aqi_db psql -U aqi_user -d aqi_db -c \
    "DELETE FROM alert_rules WHERE rule_id = '$RULE_ID';" >/dev/null 2>&1 && \
    echo "  (test rule $RULE_ID deleted)"
fi

# ---------------------------------------------------------------------------
# 6. Analytics endpoints
# ---------------------------------------------------------------------------
section "Analytics endpoints (city=$CITY)"
check "GET /api/analytics/city-comparison — 200, list"   "$API/api/analytics/city-comparison"          200 '. | type == "array"'
check "GET /api/analytics/trends weekly   — 200, list"   "$API/api/analytics/trends?city=$CITY&period=weekly"  200 '. | type == "array"'
check "GET /api/analytics/trends invalid  — 400"         "$API/api/analytics/trends?city=$CITY&period=bad"     400
check "GET /api/analytics/peak-hours      — 200, list"   "$API/api/analytics/peak-hours?city=$CITY"    200 '. | type == "array"'
check "GET /api/analytics/distribution   — 200, list"    "$API/api/analytics/distribution?city=$CITY"  200 '. | type == "array"'
check "GET /api/analytics/gaps           — 200, list"    "$API/api/analytics/gaps?city=$CITY"           200 '. | type == "array"'

# ---------------------------------------------------------------------------
# 7. OpenAPI docs reachable
# ---------------------------------------------------------------------------
section "API docs"
check "GET /docs  — 200" "$API/docs"  200
check "GET /redoc — 200" "$API/redoc" 200

# ---------------------------------------------------------------------------
# 8. Frontend dev server
# ---------------------------------------------------------------------------
section "Frontend"
check "GET http://localhost:5173/ — 200, HTML" "$FRONTEND/" 200

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL=$((PASS + FAIL))
echo ""
echo "─────────────────────────────────────────"
if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}All $TOTAL checks passed.${NC}"
  exit 0
else
  echo -e "${RED}$FAIL of $TOTAL checks FAILED.${NC}"
  exit 1
fi
