#!/usr/bin/env python3
"""
Testsigma API client — create features/scenarios/test-cases/NLP-steps/suites and
trigger test plans, entirely over the API.

Testsigma exposes two API surfaces:
  * PUBLIC   https://<host>/api/v1/...   — Bearer JWT (an API key from the UI).
             Used for: creating test cases, triggering test plans.
  * INTERNAL https://<host>/private/... and /folders, /executions — the web UI's
             own API, authenticated by the X-TS-AUTH session cookie.
             Used for: features/scenarios (folders), steps, suites.

Auth (env vars):
  TESTSIGMA_API_KEY         Bearer JWT  (UI > Settings > API Keys)
  TESTSIGMA_SESSION_COOKIE  value of the X-TS-AUTH cookie from a logged-in
                            browser session (DevTools > Application > Cookies).
  TESTSIGMA_HOST            default https://app.testsigma.com

Why a cookie? Testsigma has no public endpoint for steps/suites/features — they
live behind the UI's /private API. Grab X-TS-AUTH once from your browser; it is
a session token, so refresh it when it expires (≈ a day).

Usage:
  ts_api.py feature   --version 29 --name "Smoke"
  ts_api.py scenario  --version 29 --name "Auth" --parent <featureId>
  ts_api.py case      --version 29 --name "Welcome renders" --scenario <id>
  ts_api.py step      --case <id> --order 1000 --template 20001 --action "Launch App"
  ts_api.py step      --case <id> --order 2000 --template 20052 \
                      --action "Wait until the text Welcome is present on the current page" \
                      --testdata "Welcome"
  ts_api.py suite     --version 29 --name "Smoke" --cases 183,184,185
  ts_api.py templates --version 29 --grep "tap on text"      # find templateId
  ts_api.py trigger   --plan <testPlanId> [--env <id>] [--wait]
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

HOST = os.environ.get("TESTSIGMA_HOST", "https://app.testsigma.com").rstrip("/")
BEARER = os.environ.get("TESTSIGMA_API_KEY", "")
COOKIE = os.environ.get("TESTSIGMA_SESSION_COOKIE", "")


def _req(method, path, body=None, bearer=False):
    url = HOST + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Accept", "application/json")
    if data is not None:
        r.add_header("Content-Type", "application/json")
    if bearer:
        if not BEARER:
            sys.exit("error: TESTSIGMA_API_KEY not set (needed for this call)")
        r.add_header("Authorization", "Bearer " + BEARER)
    else:
        if not COOKIE:
            sys.exit("error: TESTSIGMA_SESSION_COOKIE not set (needed for this call)")
        r.add_header("Cookie", "X-TS-AUTH=" + COOKIE)
        r.add_header("Origin", HOST)
        r.add_header("Referer", HOST + "/ui/")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            t = resp.read().decode()
            return resp.status, (json.loads(t) if t.strip() else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _ok(status, body, what):
    if status not in (200, 201, 202):
        sys.exit(f"error creating {what}: HTTP {status}\n{body}")
    return body


# ---- entity helpers ----
def create_folder(version, name, ftype, parent=None):
    s, b = _req("POST", "/folders", {"applicationVersionId": version, "name": name,
                "type": ftype, "parentId": parent, "isStepGroup": False})
    return _ok(s, b, f"{ftype.lower()} '{name}'")


def create_case(version, name, scenario, priority=1, ctype=1):
    s, b = _req("POST", "/api/v1/test_cases", {"name": name, "applicationVersionId": version,
                "status": "READY", "priority": priority, "type": ctype, "scenarioId": scenario,
                "isStepGroup": False, "isDataDriven": False, "isManual": False}, bearer=True)
    return _ok(s, b, f"test case '{name}'")


def add_step(case, order, template, action, testdata=None, android=True, ios=True):
    sdl = []
    if testdata is not None:
        sdl = [{"key": "testData", "type": "raw", "value": testdata, "isEncrypted": False}]
    body = {"action": action, "type": "NLP_TEXT", "testCaseId": case, "templateId": template,
            "stepOrder": float(order), "stepNumber": str(int(order // 1000)),
            "priority": "MAJOR", "waitTime": 30, "stepLevelScreenshot": "ALWAYS",
            "isApplicableForAndroid": android, "isApplicableForIos": ios, "stepDataList": sdl}
    s, b = _req("POST", "/private/test_steps", body)
    return _ok(s, b, f"step '{action[:40]}'")


def create_suite(version, name, case_ids):
    s, b = _req("POST", "/private/test_suites",
                {"name": name, "appVersionId": version, "testCaseIds": case_ids, "manual": False})
    return _ok(s, b, f"suite '{name}'")


def find_templates(version, grep):
    s, b = _req("GET", f"/private/nlp_templates?size=2000&applicationVersionId={version}")
    if s != 200:
        sys.exit(f"error listing templates: HTTP {s}\n{b}")
    items = b.get("content", b) if isinstance(b, dict) else b
    g = grep.lower()
    return [(t["id"], t.get("applicationType"), t.get("grammar", ""))
            for t in items if g in (t.get("grammar", "") or "").lower()]


def trigger(plan, env=None, wait=False, interval=30, timeout=3600):
    payload = {"executionId": int(plan)}
    if env:
        payload["environmentId"] = int(env)
    s, b = _req("POST", "/api/v1/execution_results", payload, bearer=True)
    if s not in (200, 201):
        sys.exit(f"error triggering plan: HTTP {s}\n{b}")
    run_id = b.get("id") or b.get("runId")
    print(f"started run {run_id}")
    if not wait:
        return
    waited = 0
    while waited < timeout:
        time.sleep(interval); waited += interval
        s, b = _req("GET", f"/api/v1/execution_results/{run_id}", bearer=True)
        status, result = b.get("status"), b.get("result")
        print(f"  [{waited}s] status={status} result={result}")
        if status in ("STOPPED", "COMPLETED", "DONE"):
            if result in ("SUCCESS", "PASSED", "PASS"):
                print("PASSED"); return
            sys.exit(f"plan finished: result={result}")
    sys.exit("timed out")


def main():
    p = argparse.ArgumentParser(description="Testsigma API client")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("feature");  a.add_argument("--version", type=int, required=True); a.add_argument("--name", required=True)
    a = sub.add_parser("scenario"); a.add_argument("--version", type=int, required=True); a.add_argument("--name", required=True); a.add_argument("--parent", type=int, required=True)
    a = sub.add_parser("case");     a.add_argument("--version", type=int, required=True); a.add_argument("--name", required=True); a.add_argument("--scenario", type=int, required=True)
    a = sub.add_parser("step");     a.add_argument("--case", type=int, required=True); a.add_argument("--order", type=int, required=True); a.add_argument("--template", type=int, required=True); a.add_argument("--action", required=True); a.add_argument("--testdata")
    a = sub.add_parser("suite");    a.add_argument("--version", type=int, required=True); a.add_argument("--name", required=True); a.add_argument("--cases", required=True)
    a = sub.add_parser("templates");a.add_argument("--version", type=int, required=True); a.add_argument("--grep", required=True)
    a = sub.add_parser("trigger");  a.add_argument("--plan", required=True); a.add_argument("--env"); a.add_argument("--wait", action="store_true")
    args = p.parse_args()

    if args.cmd == "feature":
        print(json.dumps(create_folder(args.version, args.name, "FEATURE")))
    elif args.cmd == "scenario":
        print(json.dumps(create_folder(args.version, args.name, "SCENARIO", args.parent)))
    elif args.cmd == "case":
        print(json.dumps(create_case(args.version, args.name, args.scenario)))
    elif args.cmd == "step":
        print(json.dumps(add_step(args.case, args.order, args.template, args.action, args.testdata)))
    elif args.cmd == "suite":
        ids = [int(x) for x in args.cases.split(",")]
        print(json.dumps(create_suite(args.version, args.name, ids)))
    elif args.cmd == "templates":
        for tid, atype, grammar in find_templates(args.version, args.grep):
            print(f"{tid}\t{atype}\t{grammar}")
    elif args.cmd == "trigger":
        trigger(args.plan, args.env, args.wait)


if __name__ == "__main__":
    main()
