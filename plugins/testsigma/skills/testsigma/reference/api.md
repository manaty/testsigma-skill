# Testsigma API reference (reverse-engineered)

Base host: `https://app.testsigma.com` (or your instance). Two auth modes:
- **Bearer**: `Authorization: Bearer <API key>` — public `/api/v1/*`.
- **Cookie**: `Cookie: X-TS-AUTH=<session>` plus `Origin`/`Referer` headers —
  internal `/private/*`, `/folders`, `/executions`.

## Read (cookie)
| GET | Returns |
|---|---|
| `/private/projects?size=100` | projects (id, name, projectType) |
| `/private/applications` | apps (filter client-side by `projectId`) |
| `/private/application_versions` | versions (`application.projectId`) |
| `/folders/features?applicationVersionId=<v>` | features + nested scenarios |
| `/private/test_steps?size=2000` | steps (to model payloads) |
| `/private/nlp_templates?size=2000&applicationType=AndroidNative` | NLP grammars + `id` (templateId) |
| `/private/test_suites` | suites |
| `/executions?size=100` / `/executions/<id>` | test plans |

## Create

### Project + app + version (cookie) — `POST /private/projects`
```json
{ "name":"My iOS","projectType":"IOSNative","hasMultipleApps":false,
  "hasMultipleVersions":false,
  "applications":[ {"name":"My iOS App","applicationType":"IOSNative",
     "applicationVersions":[ {"versionName":"1.0"} ]} ] }
```
`projectType`/`applicationType`: `AndroidNative` | `IOSNative` | `WebApplication`.
Nested key is **`applicationVersions`** (not `versions`). → 201.

### Feature / Scenario (cookie) — `POST /folders`
```json
{ "applicationVersionId":29, "name":"Smoke", "type":"FEATURE", "isStepGroup":false }
{ "applicationVersionId":29, "name":"Auth", "type":"SCENARIO", "parentId":<featureId>, "isStepGroup":false }
```

### Test case (Bearer) — `POST /api/v1/test_cases`
```json
{ "name":"Welcome renders", "applicationVersionId":29, "status":"READY",
  "priority":1, "type":1, "scenarioId":<scenarioFolderId>,
  "isStepGroup":false, "isDataDriven":false, "isManual":false }
```
`scenarioId` is **required** (a `/folders` of type SCENARIO).

### NLP step (cookie) — `POST /private/test_steps`
```json
{ "action":"Wait until the text Welcome is present on the current page",
  "type":"NLP_TEXT", "testCaseId":183, "templateId":20052,
  "stepOrder":2000, "stepNumber":"2", "priority":"MAJOR", "waitTime":30,
  "stepLevelScreenshot":"ALWAYS", "isApplicableForAndroid":true,
  "isApplicableForIos":true,
  "stepDataList":[ {"key":"testData","type":"raw","value":"Welcome","isEncrypted":false} ] }
```
`action` = the template `grammar` with `${testData}` substituted. `templateId`
comes from `/private/nlp_templates`. For literal values use `stepDataList[].type:"raw"`;
to reference a parameter use `"parameter"` with `value:"<paramName>"`.

### Suite (cookie) — `POST /private/test_suites`
```json
{ "name":"Smoke", "appVersionId":29, "testCaseIds":[183,184,185], "manual":false }
```
Note the field is **`appVersionId`** here.

## Trigger a plan (Bearer) — `POST /api/v1/execution_results`
```json
{ "executionId":<testPlanId>, "environmentId":<optional> }
```
Returns a run `id`. Poll `GET /api/v1/execution_results/<id>` → `status`
(QUEUED→…→STOPPED) and `result` (SUCCESS/FAILED).

## Delete (cookie)
`DELETE /folders/<id>`, `DELETE /private/test_suites/<id>`,
`DELETE /api/v1/test_cases/<id>` (Bearer).

## Gotchas
- Public API has **no** endpoint for steps/suites/features (404/405) — use the
  cookie/`/private` API for those.
- Many list endpoints ignore filter params (e.g. `?testCaseId=`, `?projectId=`).
- `401 "No JWT token found"` on `/api/v1` = you sent the cookie instead of the
  Bearer; `401 "Invalid JWT token"` = you used the cookie value as a bearer (it's
  opaque, not a JWT). Use the right auth per surface.
