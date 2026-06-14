#!/usr/bin/env python3
"""
Example: bulk-create a smoke suite from a spec, importing ts_api helpers.

    export TESTSIGMA_API_KEY=...  TESTSIGMA_SESSION_COOKIE=...
    python3 example_build.py <appVersionId>

Edit CASES + the template ids for your platform (run
`ts_api.py templates --version <v> --grep "<text>"` to discover them).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import ts_api  # noqa: E402

# AndroidNative text-only templates (confirm with `ts_api.py templates`)
LAUNCH, VERIFY, TAP = 20001, 20052, 20187
def launch():  return (LAUNCH, "Launch App", None)
def v(t):      return (VERIFY, f"Wait until the text {t} is present on the current page", t)
def tap(t):    return (TAP,    f"Tap on text {t}", t)

CASES = {
  "Welcome screen renders":  [launch(), v("Welcome to Nexlink"), v("Create Account"), v("Log In")],
  "Email login navigation":  [launch(), tap("Log In"), v("Email"), v("Password")],
  "Register navigation":     [launch(), tap("Create Account"), v("Phone Number"), tap("Use email instead"), v("Email")],
  "Invite code entry":       [launch(), tap("Have an invitation code?"), v("Enter your invitation code")],
}

def main():
    version = int(sys.argv[1])
    feat = ts_api.create_folder(version, "Smoke", "FEATURE")["id"]
    scen = ts_api.create_folder(version, "Auth Navigation", "SCENARIO", feat)["id"]
    case_ids = []
    for name, steps in CASES.items():
        cid = ts_api.create_case(version, name, scen)["id"]
        for i, (tmpl, action, td) in enumerate(steps, 1):
            ts_api.add_step(cid, i * 1000, tmpl, action, td)
        case_ids.append(cid)
        print(f"+ case {cid}: {name} ({len(steps)} steps)")
    suite = ts_api.create_suite(version, "Smoke", case_ids)
    print(f"suite {suite['id']} with {len(case_ids)} cases")

if __name__ == "__main__":
    main()
