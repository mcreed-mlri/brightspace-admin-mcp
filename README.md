# Brightspace Admin MCP

A local [MCP](https://modelcontextprotocol.io) server that lets Claude Code talk to your
**D2L Brightspace (Valence) API** as a super admin. Read-only to start: users, org structure,
enrollments, grades, and Data Hub exports â€” plus a raw `api_get` escape hatch for exploring
any endpoint.

> **Auth model:** OAuth 2.0 **Authorization Code** grant. The server acts as *you* (the admin
> who consents once in the browser). It stores a rotating refresh token locally and refreshes
> access tokens automatically.

## 1. Register the OAuth app in Brightspace

Admin Tools â†’ **Manage Extensibility** â†’ **OAuth 2.0** â†’ **Register an app**:

| Field | Value |
|---|---|
| Application Name | `Brightspace Admin MCP` |
| Redirect URI | `https://localhost:3000/callback` (Brightspace requires HTTPS) |
| Grant type | **Authorization Code** (with refresh tokens) |
| Scope | the read-only string in `.env.example` (verify each token in the scope picker) |

Copy the **Client ID** and **Client Secret** it gives you.

## 2. Configure

```powershell
copy .env.example .env
# then edit .env: instance URL, client id/secret (scope already matches what you registered)
```

## 3. Install (uses pip, not npm)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## 4. Authorize once

```powershell
python scripts/authorize.py
```

Your browser opens, you log in + consent, and a refresh token is saved to `.tokens.json`.
The local callback is served over HTTPS with a throwaway self-signed cert, so the browser
will warn the page isn't secure â€” choose **Advanced â†’ Proceed to localhost** to finish.

## 5. Smoke test (no Claude needed)

```powershell
python scripts/smoke.py            # prints your whoami
python scripts/smoke.py --versions # lists supported API versions
```

Run it twice â€” the second run must still succeed, proving the rotated refresh token persists.

## 6. Use from Claude Code

`.mcp.json` is already in the repo. Open this folder in Claude Code, approve the MCP server,
run `/mcp` to confirm `brightspace` is connected, then try:

- "Use brightspace `whoami`."
- "Search org units of type 'Course Offering' named 'Algebra' and show the classlist of the first."
- "List the Brightspace Data Sets available for export."
- "Do a raw `api_get` on `/lp/1.43/organization/info`."

## Tools

| Area | Tools |
|---|---|
| Users | `whoami`, `get_user`, `find_user` |
| Org structure | `get_organization`, `search_orgunits`, `get_orgunit`, `get_descendants`, `list_orgunit_types` |
| Enrollments | `list_user_enrollments`, `list_orgunit_enrollments`, `get_classlist`, `get_user_enrollment` |
| Grades | `list_grade_objects`, `get_grade_object`, `get_user_grades`, `get_final_grade` |
| Data Hub | `list_brightspace_data_sets`, `list_advanced_data_sets`, `run_advanced_data_set`, `download_data_set` (disable all with `BRIGHTSPACE_ENABLE_DATAHUB=0`) |
| Exploration | `list_api_versions`; `api_get` (raw GET, **off by default** — enable with `BRIGHTSPACE_ENABLE_RAW=1`) |

## Security notes

**Access & identity**
- The server cannot modify any LMS data. Every call is a GET except `run_advanced_data_set`,
  which POSTs one thing: a Data Hub *export job* (it creates a report, never changes records).
- The token can never exceed the role of the user who authorized it. **Authorize as a
  dedicated service account with a minimal read-only admin role**, not a personal
  full-admin account — that role is the strongest control you have.
- **Revocation:** Admin Tools → Manage Extensibility → OAuth 2.0 → delete the app.
  This immediately invalidates all access and refresh tokens. Do this if `.tokens.json`
  is ever exposed.

**Data handling**
- Tool results (names, emails, grades) become part of the Claude conversation and are
  sent to the LLM provider. Confirm this is permitted under your institution's privacy
  obligations (e.g. FERPA) and your Anthropic agreement before using on student data.
- `.env` and `.tokens.json` hold secrets and are **gitignored** — never commit them.
  `.tokens.json` is a standing credential stored in plaintext: use full-disk encryption
  (BitLocker) on any machine that runs this server.
- Data Hub downloads can be large and contain PII; they save to `./exports/` (gitignored,
  unencrypted). Delete exports when you're done with them — they are bulk student data.
- Every API call is appended to `audit.log` (gitignored) — timestamp, method, URL,
  status — so you can answer "what did the AI access and when". Brightspace also logs
  API calls server-side against this OAuth app.

## Roadmap

- Write tools (enroll, create course, update grade) behind an explicit opt-in flag.
- Optional Client Credentials grant (service account + JWT) for unattended/scheduled runs.

