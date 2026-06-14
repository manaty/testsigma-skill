#!/usr/bin/env bash
# Trigger a Testsigma test plan and wait for the result. Pure curl — for CI.
#
#   TESTSIGMA_API_KEY       Bearer JWT (store as a CI secret)
#   TESTSIGMA_TEST_PLAN_ID  numeric plan id ("executionId")
#   TESTSIGMA_HOST          default https://app.testsigma.com
#   TESTSIGMA_ENV_ID        optional environmentId
#   TESTSIGMA_WAIT          "true" (default) to poll until done
set -euo pipefail
HOST="${TESTSIGMA_HOST:-https://app.testsigma.com}"
WAIT="${TESTSIGMA_WAIT:-true}"; INTERVAL="${TESTSIGMA_POLL_INTERVAL:-30}"; TIMEOUT="${TESTSIGMA_TIMEOUT:-3600}"
die(){ echo "::error::$*" >&2; exit 1; }
[ -n "${TESTSIGMA_API_KEY:-}" ] || die "TESTSIGMA_API_KEY not set"
[ -n "${TESTSIGMA_TEST_PLAN_ID:-}" ] || die "TESTSIGMA_TEST_PLAN_ID not set"
AUTH=(-H "Authorization: Bearer ${TESTSIGMA_API_KEY}")
JSON=(-H "Content-Type: application/json" -H "Accept: application/json")
body="{\"executionId\": ${TESTSIGMA_TEST_PLAN_ID}"
[ -n "${TESTSIGMA_ENV_ID:-}" ] && body="${body}, \"environmentId\": ${TESTSIGMA_ENV_ID}"
body="${body}}"
resp="$(curl -sS -m 60 -X POST "${AUTH[@]}" "${JSON[@]}" "${HOST}/api/v1/execution_results" -d "${body}")"
run_id="$(printf '%s' "$resp" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("id") or d.get("runId") or "")' 2>/dev/null || true)"
[ -n "$run_id" ] || die "could not parse run id from: $resp"
echo "started run $run_id"
[ "$WAIT" = "true" ] || exit 0
e=0
while [ "$e" -lt "$TIMEOUT" ]; do
  sleep "$INTERVAL"; e=$((e+INTERVAL))
  sr="$(curl -sS -m 60 "${AUTH[@]}" "${JSON[@]}" "${HOST}/api/v1/execution_results/${run_id}")"
  read -r status result <<EOF
$(printf '%s' "$sr" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("status",""),d.get("result",""))' 2>/dev/null || echo " ")
EOF
  echo "  [${e}s] status=${status:-?} result=${result:-?}"
  case "$status" in
    STOPPED|COMPLETED|DONE)
      case "$result" in SUCCESS|PASSED|PASS) echo "PASSED"; exit 0;; *) die "result=$result";; esac;;
  esac
done
die "timed out after ${TIMEOUT}s"
