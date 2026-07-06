# Safety Measures — Brightspace Admin MCP

This tool lets an AI assistant (Claude) look up information in our Brightspace LMS.
This page summarizes the safeguards built into it.

## It cannot change anything

- Every operation is **read-only**. The server cannot edit grades, enrollments,
  users, courses, or any other LMS record.
- The one exception is generating a Data Hub *report* (a bulk export Brightspace
  builds on request) — it creates a file, never modifies data, and can be disabled
  entirely with a single setting (`BRIGHTSPACE_ENABLE_DATAHUB=0`).
- The AI can only use a **fixed, reviewable list of ~20 tools**, each tied to one
  specific Brightspace endpoint. An "explore any endpoint" tool exists for
  development but is **off by default** and still read-only when enabled.

## Access is limited and revocable

- The server uses standard **OAuth 2.0** — the same mechanism Brightspace approves
  for all integrations — and can never exceed the permissions of the staff account
  that authorized it.
- Access can be **revoked instantly** at any time: Admin Tools → Manage
  Extensibility → OAuth 2.0 → delete the app. All tokens die immediately.
- Requests are pinned to our Brightspace instance only; the server runs locally on
  a staff machine and accepts no inbound connections from anywhere.

## Everything is logged

- Every single API call is written to a local **audit log** (timestamp, what was
  requested, result) — we can always answer *"what did the AI access, and when?"*
- Brightspace independently logs the same calls on its side, attributed to this
  specific app registration.

## Data handling

- Credentials live only in local files that are excluded from version control;
  the machine uses full-disk encryption.
- Results are **capped** (default 200 records per query) so broad searches can't
  sweep large amounts of student data by accident.
- Bulk exports (if enabled) save to a local, version-control-excluded folder, are
  flagged with a PII warning, and are deleted when no longer needed.

## Where does the data go?

Exactly two places, both over encrypted connections:

1. **Brightspace** — the server talks directly to our own instance; the code refuses
   to contact any other host. No intermediary or third-party service sits in between.
2. **Anthropic** — what the AI retrieves becomes part of the conversation it is
   processing (see the caveat below).

It does **not** go anywhere shared or public. The server is a local program on a
staff machine — not a cloud service, not listed in any directory, with no address
that other AI agents, services, or people could connect to. Connected tools cannot
read the conversation; each tool only receives the specific request sent to it.
One operational rule follows from this: avoid enabling outbound connectors (e.g.,
email) in the same AI session unless intended, since the AI itself could be asked
to pass retrieved data along to them.

## The honest caveat

Information the AI retrieves (e.g., a student's name, email, or grade) becomes part
of the AI conversation, which is processed by Anthropic (the AI provider). Whether
that is acceptable for student records is a **policy decision** — it depends on our
privacy obligations and our agreement with Anthropic, and should be confirmed before
this tool is used on real student data.
