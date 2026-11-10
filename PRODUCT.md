# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite + TypeScript with plain CSS (frontend, Vercel); FastAPI (backend, Render); Neon Postgres. Chosen by the user in Step 2 of the assignment.

## Users

- **Compliance analyst** at a payment gateway licensed by the National Bank of Ethiopia. Works at a desk on a desktop
  browser through a queue of merchant applications and monitoring cases; makes the approve/reject decision and
  confirms or dismisses sanctions hits.
- **Merchant** (business owner or staff) applying to accept payments, mostly from a phone; uploads licences, TIN
  certificates, memoranda and IDs, and answers information requests through a link in an email.

## Product Purpose

Wekil is an AI KYB and compliance analyst. It prepares every onboarding decision: reads documents (Gemini), checks
them against each other and the application, looks up registries, screens owners against the OFAC and UN lists with
written triage, scores risk, drafts the decision memo, and chases merchants by email with calendar due dates. Each
morning it rescreens approved merchants, opens renewal and periodic-review cases, and sends reminders. Success: an
analyst clears a much larger queue in minutes per merchant, and nothing regulators examine is forgotten.

## Positioning

Every verdict shows its evidence (the document field, list entry or registry record it came from), and the agent
never approves, confirms a true match or files anything: it prepares, a human decides (maker-checker).

## Operating Context

Ethiopian payment-gateway back office: required-documents matrix by legal form (sole trader, PLC, share company),
risk tiers low/medium/high/prohibited, periodic reviews every 6/12/24 months, 30-day document-expiry window,
append-only audit trail. Merchants answer through signed upload links that expire after 7 days.

## Capabilities and Constraints

- Free tiers only, no payment card anywhere (Gemini free tier, Render, Vercel, Neon, GitHub Actions cron).
- Gemini free-tier inputs may be used by Google, so demo data is synthetic only.
- The Ethiopian business register has no public API; that check is a clearly labelled simulation.

## Evidence on Hand

Synthetic demo merchants and watermarked SPECIMEN documents in `backend/demo/`. No real customers, testimonials or
metrics exist; do not fabricate any.

## Product Principles

1. Evidence before opinion: show where every finding came from.
2. The human decides; the agent prepares, recommends and follows up.
3. Plain language for merchants; precise language for analysts.
4. Never lose a case: every action is logged and every open item has an owner and a date.

## Accessibility & Inclusion

Merchants use low-end phones on slow connections: mobile-first, small payloads, large touch targets. WCAG AA contrast
and full keyboard use for the analyst console.
