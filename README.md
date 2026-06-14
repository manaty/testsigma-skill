# Testsigma skill

A [Claude Code](https://claude.com/claude-code) skill (and reference for any LLM)
that **authors and runs [Testsigma](https://testsigma.com) tests entirely over
the API** — features, scenarios, test cases, NLP steps, and suites — then
triggers test plans for CI/CD.

It works around the catch that Testsigma's *public* API can't create
steps/suites/features: the skill also uses the UI's *internal* `/private` API via
a session cookie. See [the skill](plugins/testsigma/skills/testsigma/SKILL.md) and
[API reference](plugins/testsigma/skills/testsigma/reference/api.md).

## Install in Claude Code

**As a plugin (recommended):**
```
/plugin marketplace add manaty/testsigma-skill
/plugin install testsigma@testsigma-skill
```

**Or just the skill (clone into your skills dir):**
```bash
git clone https://github.com/manaty/testsigma-skill /tmp/tss \
  && mkdir -p ~/.claude/skills \
  && cp -r /tmp/tss/plugins/testsigma/skills/testsigma ~/.claude/skills/testsigma
```
Then start Claude Code and ask it to "use the testsigma skill".

## Use with ChatGPT / other LLMs

There's no plugin system, but the skill is self-contained Markdown + a stdlib
Python CLI. Paste
[`SKILL.md`](plugins/testsigma/skills/testsigma/SKILL.md) and
[`reference/api.md`](plugins/testsigma/skills/testsigma/reference/api.md) into a
Custom GPT's instructions (or any chat), and ship
[`scripts/ts_api.py`](plugins/testsigma/skills/testsigma/scripts/ts_api.py) as a
tool the model can run.

## Configure (env vars)

```bash
export TESTSIGMA_HOST="https://app.testsigma.com"      # your instance
export TESTSIGMA_API_KEY="<Bearer JWT — UI > Settings > API Keys>"
export TESTSIGMA_SESSION_COOKIE="<X-TS-AUTH cookie from a logged-in browser>"
```

## Quick start

```bash
cd plugins/testsigma/skills/testsigma
FEATURE=$(scripts/ts_api.py feature  --version 29 --name "Smoke" | jq .id)
SCEN=$(scripts/ts_api.py scenario --version 29 --name "Auth" --parent $FEATURE | jq .id)
CASE=$(scripts/ts_api.py case --version 29 --name "Welcome renders" --scenario $SCEN | jq .id)
scripts/ts_api.py step --case $CASE --order 1000 --template 20001 --action "Launch App"
scripts/ts_api.py step --case $CASE --order 2000 --template 20052 \
   --action "Wait until the text Welcome is present on the current page" --testdata "Welcome"
scripts/ts_api.py suite --version 29 --name "Smoke" --cases $CASE
scripts/ts_api.py trigger --plan <planId> --wait
```

## What it can / can't do over the API

| Entity | API? |
|---|---|
| Project / app / app-version | ✅ `POST /private/projects` |
| Feature / Scenario | ✅ `POST /folders` |
| Test case | ✅ `POST /api/v1/test_cases` (needs `scenarioId`) |
| NLP step (text-based) | ✅ `POST /private/test_steps` (needs `templateId`) |
| NLP step (element-based) | ⚠️ needs an element captured in the UI/recorder |
| Suite | ✅ `POST /private/test_suites` |
| Test plan (device + app binding) | ⚠️ create once in the UI; **trigger** via API |

## License

MIT © Manaty
