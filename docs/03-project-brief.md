# Project brief: Wekil

A short explanation of the whole project, for presenting and answering questions about it.

## The problem

A payment gateway can't let a business take payments until it has verified that business (KYB) and keeps that
verification current. The analyst who does this reads licences, TIN certificates, memoranda and IDs, checks them
against each other and the registry, screens the owners against sanctions lists (where 85–95% of hits are false
positives), assigns a risk tier, writes a memo, chases merchants for missing papers, and later tracks expiring
documents, periodic reviews and new sanctions designations. It's slow (3–7 days per merchant by hand), expensive,
and mistakes bring large fines (Starling £29M, Cash App $40M).

## Why this role

You built this exact workflow in the back office of a regulated Ethiopian payment gateway. The work is mostly
reading, comparing, explaining and chasing, which an LLM agent does well, while the decision itself must stay with a
human (maker-checker). It's also a domain few candidates would pick, and it avoids HR/recruiting.

## What Wekil does

1. **Merchant applies** on a mobile-first portal (business, owners, documents).
2. **Wekil reviews automatically:** Gemini reads each document into fields; code cross-checks names, TINs, owners and
   expiry dates; it looks up the registry (GLEIF, UK Companies House, simulated Ethiopian register); it screens the
   business and owners against the OFAC and UN lists with a name matcher built for Ethiopian names, then Gemini
   triages each candidate with reasons; rules produce a risk tier; Gemini writes a decision memo.
3. **If something is missing or wrong,** Wekil emails the merchant from Gmail with exactly what to send and a signed
   upload link, and puts the due date on Google Calendar. Re-uploads trigger a re-review.
4. **The analyst decides** in the console, seeing every finding next to its source. Approving stamps the file, emails
   the merchant and schedules the next periodic review by tier.
5. **Every morning** (GitHub Actions cron): rescreen approved merchants against new list entries, renewals 30 days
   before expiry, periodic reviews, reminders with a firmer tone each time, escalation, and a digest email.
6. **Command bar:** plain-English questions and actions through Gemini function calling. Anything that writes
   (emails, calendar) is shown as a plan and only runs when the analyst confirms.

## How it's built

- **Backend:** FastAPI (Python 3.12) on Render's free tier, Docker. One module per concern: `workflow.py` (review state
  machine), `routine.py` (morning job), `commands.py` (command bar), and `tools/` (gemini, documents, screening,
  registry, risk, google). Postgres on Neon; the audit log is append-only.
- **Frontend:** React + Vite + TypeScript, plain CSS, on Vercel. Analyst console (Today, Applications, Monitoring,
  workspace) and merchant portal (apply, upload). Its look comes from security print: guilloche seals, serial-number
  IDs, intaglio ink.
- **Integrations:** Gemini (AI Studio key), Gmail API, Google Calendar API, OFAC and UN sanctions lists, GLEIF, UK
  Companies House.
- **No card anywhere:** GCP's free tier needs billing, so the cron runs on GitHub Actions and the API on Render; moving
  to Cloud Run and Cloud Scheduler is a redeploy.

## Design decisions worth defending

- **Fixed workflow + LLM judgement**, not an autonomous agent loop: predictable, auditable, cheap on free-tier quota.
- **Code does arithmetic and matching; Gemini reads, triages and writes.** Gemini output must fit a schema.
- **The agent never approves, confirms a match or files anything.** It prepares; the human decides.
- **Prompt-injection safety:** document and email text is data; recipients and next steps come from the workflow.
- **Ethiopian names:** given name + father's + grandfather's name, and transliteration variants (Germay/Ghermay);
  the matcher compares token by token so these still match.

## Honest limits

Synthetic data only (Gemini free tier may use inputs); the Ethiopian register is simulated; the demo sanctions entry
is synthetic and labelled; the Google OAuth app is in testing mode, so its token expires after 7 days; Render's free
instance sleeps after 15 idle minutes.

## Links

- App: https://wekil-lilac.vercel.app · portal: https://wekil-lilac.vercel.app/apply
- API docs: https://wekil-api.onrender.com/docs
- Code: https://github.com/abeni-al7/ai-agent
