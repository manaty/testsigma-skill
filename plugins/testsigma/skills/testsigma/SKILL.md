---
name: testsigma
description: Author and run Testsigma tests entirely over the API — create features, scenarios, test cases, NLP steps, and test suites, then trigger test plans for CI/CD. Use when the user wants to programmatically build or run Testsigma test automation (mobile/web), bulk-create test cases, or wire Testsigma into a pipeline. Works around the fact that Testsigma's public API can't author steps/suites by also using the UI's internal /private API via a session cookie.
---

# Testsigma over the API

Testsigma is normally authored by clicking through its web UI. This skill drives
it programmatically instead, so you can bulk-create test assets from a spec and
trigger runs in CI. The non-obvious part: **Testsigma has two API surfaces**, and
authoring requires both.

## The two API surfaces

| Surface | Base | Auth | Creates |
|---|---|---|---|
| Public | `/api/v1/*` | `Authorization: Bearer <API key>` | **test cases**, **triggers plans** |
| Internal (the UI's own) | `/private/*`, `/folders`, `/executions` | `Cookie: X-TS-AUTH=<session>` | **features**, **scenarios**, **steps**, **suites** |

The public API key alone **cannot** create steps, suites, or features — those
endpoints don't exist there (404/405). You must also grab the `X-TS-AUTH` session
cookie from a logged-in browser. It's a session token; refresh it when it expires.

## Setup

```bash
export TESTSIGMA_HOST="https://app.testsigma.com"     # your instance
export TESTSIGMA_API_KEY="<Bearer JWT from UI > Settings > API Keys>"
export TESTSIGMA_SESSION_COOKIE="<X-TS-AUTH cookie value>"
```
Get the cookie: log into Testsigma in a browser → DevTools → Application →
Cookies → copy the value of `X-TS-AUTH`.

All commands below use `scripts/ts_api.py` (stdlib only, no deps).

## The object model (build bottom-up)

```
Project → Application → Application Version (an uploaded build)
  └─ Feature (folder)
       └─ Scenario (folder)
            └─ Test Case
                 └─ NLP Steps
Suite  = a named set of test cases (for a version)
Plan   = suites + device/environment config (this is what CI triggers)
```

You need the **application version id** (not the project id) to attach features
and cases. Find it under the project's app version in the UI, or
`GET /private/application_versions`.

## Workflow

### 1. Create the folder hierarchy
```bash
FEATURE=$(scripts/ts_api.py feature  --version 29 --name "Smoke" | jq .id)
SCEN=$(scripts/ts_api.py scenario --version 29 --name "Auth Navigation" --parent $FEATURE | jq .id)
```

### 2. Create a test case
```bash
CASE=$(scripts/ts_api.py case --version 29 --name "Welcome screen renders" --scenario $SCEN | jq .id)
```

### 3. Add NLP steps
Steps reference a **templateId** (an NLP grammar). Find the right template:
```bash
scripts/ts_api.py templates --version 29 --grep "tap on text"
# 20187   AndroidNative   Tap on text ${testData}
```
The `--action` text must be the grammar with `${testData}` substituted; pass the
substituted value again as `--testdata` (for templates that take test data).
```bash
scripts/ts_api.py step --case $CASE --order 1000 --template 20001 --action "Launch App"
scripts/ts_api.py step --case $CASE --order 2000 --template 20052 \
   --action "Wait until the text Welcome is present on the current page" --testdata "Welcome"
scripts/ts_api.py step --case $CASE --order 3000 --template 20187 \
   --action "Tap on text Log In" --testdata "Log In"
```
`--order` controls step sequence (use 1000, 2000, …). Text-based templates
(`Launch App`, `Wait until the text … is present`, `Tap on text …`) need **no UI
element/recorder** — prefer them for portable smoke tests. Element steps
(`#{uiIdentifier}`) need a captured element and are best recorded in the UI.

Common text-only template ids differ per platform — always confirm with
`templates --grep`. Examples seen on AndroidNative: `20001` Launch App,
`20052` wait-until-text-present, `20187` tap-on-text. Web uses `1044` Navigate to
url, `1` wait-until-text-present.

### 4. Group cases into a suite
```bash
scripts/ts_api.py suite --version 29 --name "Smoke" --cases $CASE,184,185
```

### 5. Create the test plan (UI step) and trigger it
Plan creation binds suites to a **device + uploaded app build** on Testsigma's
cloud. That device/app binding is fiddly over the API; create the plan once in
the UI (New Test Plan → add suite → pick device → bind the app build → Save) and
note its id. Then trigger it anywhere (CI):
```bash
scripts/ts_api.py trigger --plan <planId> --wait      # exits non-zero on failure
```
Or use `scripts/run-testsigma.sh` (pure curl, for GitHub Actions). See
[reference/github-actions.yml](reference/github-actions.yml).

## Bulk creation

To create many cases, loop in your own script importing the helpers, or call the
CLI per case. A spec like `{case_name: [(templateId, action, testdata), …]}` maps
directly onto step calls. See [reference/example_build.py](reference/example_build.py).

## Full endpoint reference

See [reference/api.md](reference/api.md) for the raw endpoints, payloads, and the
field gotchas (`scenarioId` on cases, `appVersionId` vs `applicationVersionId` on
suites, `type: NLP_TEXT` on steps).

## Notes & gotchas
- Test case create needs `scenarioId` (a folder of `type: SCENARIO`), `status`,
  `priority`, `type`. Without `scenarioId` the public API returns
  *"Scenario Id is needed to create a test case"*.
- Suite version field is `appVersionId` (the public/case field is
  `applicationVersionId` — don't mix them up).
- List endpoints often **ignore filter params** (e.g. `?testCaseId=`); don't rely
  on them for verification — trust the create responses (they echo `testCaseId`).
- The session cookie expires; on 401 *"No JWT token found"* re-grab `X-TS-AUTH`.
