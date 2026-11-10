# Demo script

About 1095 words, roughly 8 minutes at a calm pace. Read each scene as one take or the whole thing in one go; leave a short pause between scenes. The screen notes are for orientation only.

## S01: Wekil console, Today page

Hi, I'm Abenezer. For this assignment I automated a role I know from the inside: the merchant onboarding and compliance analyst at a payment gateway. Before a business can take a single payment, someone has to check who it is, whether its papers are real and current, and whether its owners are on a sanctions list. At banks a corporate KYC review costs around two and a half thousand dollars and takes weeks. For merchants it still takes three to seven days, and most applicants give up when onboarding drags. This is Wekil, an AI analyst that does the preparation and the follow-up, so the human only makes the decision.

## S02: GitHub: research and breakdown document

I started from my own work. I built the back office of a regulated Ethiopian payment gateway, so I broke this analyst's job into eleven sub-functions, from intake to suspicious transaction reports, and mapped how they depend on each other. Everything rests on reading the documents correctly. Then I scored each one on value, frequency and how automatable it is. Document extraction, sanctions screening and daily monitoring came out on top, followed by risk scoring, intake and chasing merchants. Bank verification and filing reports stay with humans, because filing is a legal act.

## S03: GitHub: solution design, architecture and onboarding flow

The design keeps the agent accountable. A fixed workflow runs every application: a completeness check, Gemini reads the documents, code cross-checks them, a registry lookup, sanctions screening, a risk tier, and then either an information request or a decision memo. Arithmetic and name matching are plain code. Gemini does the reading, the triage and the writing. The frontend is React on Vercel, the backend is FastAPI on Render, and the data is in Postgres on Neon. Cloud Run and Cloud Scheduler need a billing account, so to stay card-free a GitHub Actions cron calls the same endpoint Cloud Scheduler would. The integrations are Gemini, Gmail, Google Calendar, the official OFAC and UN sanctions lists, GLEIF and UK Companies House.

## S04: Merchant portal: Selam Coffee Roasters applies

Let's see it work. A coffee roaster in Bole applies from the merchant portal. There are three steps: the business, its owners, and the documents, which here are a business licence, a TIN certificate and the owner's ID. Every document in this demo is synthetic and watermarked. I send the application.

## S05: Console: Selam's application being reviewed live

In the console, Wekil is already reviewing it. Each line in the audit trail is one step. It reads every document with Gemini into structured fields, compares the names, TIN, owners and expiry dates across the documents and against the form, checks the business register, and screens the business and its owner against about eighteen thousand OFAC and UN entries. When it finishes, it prints a seal on the file. The linework encodes the risk tier, and the memo says what was verified and what is still open. Each document sits next to the fields Wekil read from it, so I can check its work.

## S06: Console: Blue Horizon Trading, sanctions near-match, approval

Blue Horizon Trading is more interesting. One owner, Ermias Germay Tekle, closely resembles a real entry on the US Treasury list. A name match alone would block this merchant for days. Wekil compares the evidence: the listed person was born in the seventies, our owner was born in nineteen ninety-six, and the full names differ. So it marks the hit as likely not the same person, and says why. The decision is still mine. I dismiss both candidates and approve. A registrar's stamp lands on the seal, the merchant gets an approval email, and the next periodic review goes on the compliance calendar, based on the risk tier.

## S07: Gmail: Wekil's request to Tana Spice Traders; upload page

Tana Spice Traders sent an expired licence and forgot their TIN certificate. Wekil didn't wait for a human. It emailed them from my Gmail with exactly what is missing and a secure upload link, and put the due date on the calendar. Here is that email in the merchant's inbox. The merchant follows the link, uploads a renewed licence and the TIN certificate, and sends them.

## S08: Console: Tana re-reviewed automatically

Back in the console, the upload restarted the review on its own. The new licence is valid and the TIN certificate matches, so Tana moves to ready for decision, with a fresh memo.

## S09: GitHub Actions: the morning routine runs

The proactive part runs every morning. GitHub Actions calls the routine at six o'clock Addis Ababa time, and I'm triggering it now. For this demo I added one clearly labelled synthetic entry to today's sanctions list update.

## S10: Console Today: cases from the routine; Gmail digest

Wekil downloads both lists and rescreens every approved merchant against the new entries only. It found that an owner of Hawassa Fresh Produce matches the new entry, and opened a case for me. It opened a renewal for Lalibela Crafts, whose licence expires in nineteen days, and emailed them an upload link. It reminded Merkato Mobile, whose reply is overdue. And it sent me a digest of what needs me today.

## S11: Console: command bar plans and sends reminders

For everything else there is the command bar. I ask in plain English, and Wekil calls its own tools to search, explain risk or screen a name. Anything that sends an email or changes the calendar comes back as a plan, and nothing happens until I confirm it.

## S12: GitHub: backend code

A quick look at the code. The backend is one FastAPI app with a module per concern. workflow dot py is the review state machine, and every step writes to an append-only audit log. The Gemini module is the only doorway to the model: a prompt and a schema go in, a validated object comes out, with a fallback across free-tier models. The screening module matches names token by token, so a grandfather's name or a spelling like Germay and Ghermay still matches, and only then asks Gemini to triage with evidence. The command module gives Gemini function calling over the same tools, but the model never executes a write tool. The routine module is the morning job, and this workflow file is the cron that calls it.

## S13: GitHub: frontend code

The frontend is React and TypeScript with plain CSS. The workspace page polls the API while Wekil works and lays out the memo, the hits and the documents side by side. The seal is drawn from hypotrochoid curves, so the pattern itself encodes the tier. The merchant portal is mobile-first, because most merchants here apply from their phones.

## S14: Wekil console, Today page

So, would you pay for this? One analyst can clear a much larger queue, merchants hear back in minutes instead of days, and nothing a regulator examines gets forgotten. Would you hire it over a human? For the preparation and the follow-up, yes. For the decision, deliberately no. Everything runs on free tiers with no card, and all the data in this demo is synthetic. Thanks for watching.
