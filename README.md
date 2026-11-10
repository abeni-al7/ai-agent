# Wekil

**An AI KYB and compliance analyst for payment gateways.** Wekil (ወኪል, "agent" in Amharic) prepares every merchant
onboarding decision at an Ethiopian payment gateway: it reads the documents, cross-checks them, looks up registries,
screens owners against the official sanctions lists, scores risk, drafts the decision memo and chases merchants for
what is missing. The analyst only decides. Every morning it also rescreens approved merchants, opens renewal and
periodic-review cases, sends reminders and emails a digest.

- Live app: https://wekil-lilac.vercel.app (analyst console) · https://wekil-lilac.vercel.app/apply (merchant portal)
- API: https://wekil-api.onrender.com/docs (free tier: the first request after 15 idle minutes takes about a minute)
- Research and breakdown: [docs/01-research-and-breakdown.md](docs/01-research-and-breakdown.md)
- Solution design: [docs/02-solution-design.md](docs/02-solution-design.md) (PDF: [docs/Wekil-Design.pdf](docs/Wekil-Design.pdf))

## What it does

| Step | Wekil | The analyst |
|---|---|---|
| Intake | Checks uploads against the document matrix for the legal form | |
| Documents | Gemini reads each licence, TIN certificate, memorandum and ID into fields; code cross-checks names, TINs, owners and expiry dates | Judges doubtful documents |
| Registry | GLEIF (LEI), UK Companies House, and a labelled simulation of the Ethiopian register (no public API exists) | |
| Sanctions | Name matching in code against the OFAC SDN and UN lists (18k+ entries), then Gemini triages each candidate with reasons | Confirms or dismisses each hit |
| Risk and memo | Rule-based score and tier; Gemini drafts the memo | **Approves or rejects** |
| Follow-up | Emails requests with a signed upload link (Gmail API), puts due dates on Google Calendar, re-reviews on upload | |
| Every morning | Rescreens on list changes, renewals 30 days before expiry, periodic reviews by tier, reminders, digest | Works the cases |
| Command bar | Plain-English questions and actions via Gemini function calling; any email or calendar action waits for confirmation | Confirms |

## Architecture

```
React + Vite (Vercel) ──REST──> FastAPI (Render, Docker) ──> Neon Postgres
                                   │  ├─ Gemini API (AI Studio key)
GitHub Actions cron ──POST──>      │  ├─ Gmail API, Google Calendar API
  /api/jobs/daily (06:00 EAT)      │  └─ OFAC + UN lists, GLEIF, Companies House
```

Everything runs on free tiers with no payment card. GCP's free tier needs a billing account, so the scheduled job is a
GitHub Actions cron instead of Cloud Scheduler, and the API runs on Render instead of Cloud Run (it is a container, so
moving it is a redeploy).

```
backend/src/wekil/
  workflow.py   the review state machine (intake → documents → registry → screening → risk → request or memo)
  routine.py    the morning routine
  commands.py   the command bar (Gemini function calling; write tools need confirmation)
  tools/        gemini, documents, screening, registry, risk, google (Gmail + Calendar)
  api/          merchant (portal), analyst (console), jobs (cron)
  db.py         tables; the audit log is append-only
frontend/src/
  console/      Today, Applications, Monitoring, application workspace, command bar
  portal/       apply and upload pages for merchants
  Seal.tsx      the guilloche seal printed on each reviewed application
```

## Run locally

```bash
# backend (needs backend/.env, see below)
cd backend && uv sync && uv run uvicorn wekil.main:app --reload
uv run python demo/seed.py reset        # demo merchants; reviews two of them for real
uv run python demo/seed.py list-update  # synthetic sanctions entry for the routine demo
DATABASE_URL=sqlite:///:memory: uv run pytest

# frontend
cd frontend && npm install && npm run dev
```

`backend/.env`: `DATABASE_URL`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
(from `uv run python scripts/google_auth.py`), `COMPANIES_HOUSE_KEY`, `APP_SECRET`, `CRON_SECRET`, `ANALYST_EMAIL`,
`ANALYST_PASSWORD`, `FRONTEND_URL`.

## Honest limits

- All merchants, people and documents are synthetic (documents are watermarked SPECIMEN); the Gemini free tier may use
  inputs to improve Google's products.
- The Ethiopian business register check is simulated; the `DEMO` sanctions entry used to show rescreening is synthetic
  and labelled as such. OFAC, UN, GLEIF and Companies House data are real.
- The Google OAuth app is in testing mode, so its refresh token expires after 7 days.
