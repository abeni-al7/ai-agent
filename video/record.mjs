// Records the Wekil demo: a real browser driven at human pace, captured frame by frame, paced to the narration.
//   node record.mjs [--timing out/audio/durations.json] [--only S01,S02] [--out out/run]
// Each scene lasts at least as long as its narration; build.mjs then places each audio clip at its scene start.

import { execFileSync, execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { CURSOR_SCRIPT, Human, sleep } from "./human.mjs";

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const HERE = path.dirname(new URL(import.meta.url).pathname);
const ROOT = path.resolve(HERE, "..");
const OUT = path.resolve(HERE, arg("--out", "out/run"));
const TIMING = JSON.parse(fs.readFileSync(path.resolve(HERE, arg("--timing", "out/audio/durations.json")), "utf8"));
const ONLY = new Set((arg("--only", "") || "").split(",").filter(Boolean));
const APP = "https://wekil-lilac.vercel.app";
const API = "https://wekil-api.onrender.com";
const GH = "https://github.com/abeni-al7/ai-agent";
const DOCS = path.join(ROOT, "backend/demo/documents");
const UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36";

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(path.join(OUT, "frames"), { recursive: true });

// ---------- capture ----------
const frames = []; // [file, ms]
let cdp, capturing = false;
async function capture(page) {
  if (cdp) await cdp.detach().catch(() => {});
  cdp = await page.context().newCDPSession(page);
  cdp.on("Page.screencastFrame", async ({ data, sessionId }) => {
    if (capturing) {
      const f = `f${String(frames.length).padStart(6, "0")}.jpg`;
      fs.writeFileSync(path.join(OUT, "frames", f), Buffer.from(data, "base64"));
      frames.push([f, Date.now()]);
    }
    cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1080 });
}

// ---------- browser ----------
const ctx = await chromium.launchPersistentContext(path.join(process.env.HOME, ".playwright-mcp/profile"), {
  channel: "chrome", headless: true, viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1.2, userAgent: UA,
  args: ["--hide-scrollbars", "--disable-blink-features=AutomationControlled"],
});
await ctx.addInitScript(CURSOR_SCRIPT);
const page = ctx.pages()[0] ?? (await ctx.newPage());
const h = new Human(page);

async function go(url) {
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await capture(page);
  await page.mouse.move(h.x, h.y);
  await sleep(700);
}

// Analyst session: log in through the API with the password from backend/.env (never printed).
const env = Object.fromEntries(fs.readFileSync(path.join(ROOT, "backend/.env"), "utf8").split("\n")
  .filter((l) => l.includes("=")).map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)]));
const login = await (await fetch(`${API}/api/login`, { method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: env.ANALYST_EMAIL, password: env.ANALYST_PASSWORD }) })).json();
await page.goto(`${APP}/login`);
await page.evaluate((t) => localStorage.setItem("wekil.token", t), login.token);
const merchantId = async (name) => {
  const rows = await (await fetch(`${API}/api/merchants`, { headers: { Authorization: `Bearer ${login.token}` } })).json();
  return rows.find((r) => r.name.startsWith(name))?.id;
};
const waitStatus = async (name, done, maxMs = 240000) => {
  const end = Date.now() + maxMs;
  while (Date.now() < end) {
    const rows = await (await fetch(`${API}/api/merchants`, { headers: { Authorization: `Bearer ${login.token}` } })).json();
    if (done.includes(rows.find((r) => r.name.startsWith(name))?.status)) return true;
    await sleep(2500);
  }
  return false;
};
const openMerchant = async (name) => {
  await go(`${APP}/queue`);
  await sleep(1200);
  await h.click(page.locator(".table__name", { hasText: name }));
  await page.waitForSelector(".ws-head h1");
  await sleep(900);
};

const codeLine = async (needle) => {
  const n = await page.evaluate((t) => {
    const lines = (document.querySelector("textarea.react-blob-print-hide")?.value ?? "").split("\n");
    return lines.findIndex((l) => l.includes(t)) + 1;
  }, needle);
  return n > 0 ? page.locator(`.react-line-number[data-line-number="${n}"]`).first() : null;
};
const showCode = async (file, needle, dwell) => {
  await go(`${GH}/blob/main/${file}`);
  await page.waitForSelector("textarea.react-blob-print-hide", { timeout: 30000 }).catch(() => {});
  await sleep(900);
  const line = await codeLine(needle);
  if (line) await h.scrollTo(line, { offset: 230 }).catch(() => {});
  await h.drift(dwell);
};

// ---------- scenes ----------
const SCENES = {
  async S01(t) {
    await go(APP);
    await page.waitForSelector(".decisions, .empty");
    await h.hover(".page-head h1", 1600);
    await h.hover(".decision >> nth=0", 1500).catch(() => {});
    await h.hover(".rows", 1500).catch(() => {});
    await h.hover(".log", 1500).catch(() => {});
    await h.drift(t - 7000);
  },
  async S02() {
    await go(`${GH}/blob/main/docs/01-research-and-breakdown.md`);
    await h.hover("article h1", 1200);
    await h.scrollTo('article h2:has-text("3. The cost")', { offset: 120 });
    await h.drift(5000);
    await h.scrollTo('article h2:has-text("4. Sub-functions")', { offset: 100 });
    await h.drift(6500);
    await h.scrollTo('article h3:has-text("Dependencies")', { offset: 90 });
    await h.drift(6500);
    await h.scrollTo('article h2:has-text("5. Prioritization")', { offset: 100 });
    await h.drift(7000);
  },
  async S03() {
    await go(`${GH}/blob/main/docs/02-solution-design.md`);
    await h.scrollTo('article h2:has-text("4. How the agent acts")', { offset: 90 });
    await h.drift(14000);
    await h.scrollTo('article h2:has-text("3. Architecture")', { offset: 90 });
    await h.drift(12000);
    await h.scrollTo('article h2:has-text("5. Third-party APIs")', { offset: 90 });
    await h.drift(6000);
  },
  async S04() {
    await go(`${APP}/apply`);
    await h.type('input >> nth=0', "Selam Coffee Roasters", { fast: true });
    await h.hover('text=Sole trader', 500);
    await h.type('label:has-text("Registration number") input', "AA/14/7/2/0019482/2015", { fast: true });
    await h.type('label:has-text("TIN") input', "0045812736", { fast: true });
    await h.type('label:has-text("Business address") input', "Bole Sub-city, Woreda 03, Addis Ababa", { fast: true });
    await h.type('label:has-text("Email for updates") input', "abenezeralebachew3+selam@gmail.com", { fast: true });
    await h.type('label:has-text("Phone") input', "+251 911 402 118", { fast: true });
    await h.type('label:has-text("Expected payments") input', "850000", { fast: true });
    await h.click('button:has-text("Continue to owners")');
    await h.type('label:has-text("Full name") input', "Selamawit Bekele Haile", { fast: true });
    await h.click('label:has-text("Date of birth") input');
    await page.keyboard.type("04181990", { delay: 70 });
    await h.click('button:has-text("Continue to documents")');
    const picks = page.locator(".pick");
    for (const [i, f] of [[0, "business_license.pdf"], [1, "tin_certificate.pdf"], [2, "owner_id.png"]]) {
      await h.to(picks.nth(i));
      await sleep(350);
      await picks.nth(i).locator("input").setInputFiles(path.join(DOCS, "selam", f));
      await sleep(600);
    }
    await h.click('button:has-text("Send application")');
    await page.waitForSelector("text=Application received", { timeout: 90000 });
    await h.hover(".serial", 1500);
  },
  async S05(t) {
    const t0 = Date.now();
    await openMerchant("Selam Coffee");
    await h.hover(".trail", 2000);
    await waitStatus("Selam Coffee", ["ready", "needs_attention", "awaiting_merchant"]);
    await sleep(4500); // let the page poll and the seal print
    await h.hover(".ws-head .seal", 2200);
    await h.scrollTo(".memo", { offset: 110 });
    await h.drift(Math.max(4000, Math.min(9000, t - (Date.now() - t0) - 9000)));
    await h.scrollTo("#documents", { offset: 90 });
    await h.hover(".doc >> nth=0", 2500);
    await h.hover(".doc__fields dl >> nth=0", 2500);
  },
  async S06() {
    await openMerchant("Blue Horizon");
    await h.scrollTo("#screening", { offset: 90 });
    await h.hover(".hit__pair >> nth=0", 3500);
    await h.hover(".hit__reasons >> nth=0", 5500);
    for (let i = 0; i < 2; i++) {
      await h.click(page.locator('button:has-text("Not the same, dismiss")').first());
      await sleep(2200);
    }
    await h.scroll(-3000, 1600);
    await sleep(500);
    await h.click('button:has-text("Approve merchant")');
    await page.waitForSelector(".stamp", { timeout: 60000 });
    await sleep(600);
    await h.hover(".ws-head .seal", 3000);
    await h.hover(".trail", 2500);
  },
  async S07() {
    await go("https://mail.google.com/mail/u/0/#search/to%3Aabenezeralebachew3%2Btana%40gmail.com");
    await page.waitForSelector("tr.zA", { timeout: 60000 });
    await sleep(1200);
    await h.click(page.locator("tr.zA").first());
    const link = page.locator('a[href*="wekil-lilac.vercel.app/upload/"]').first();
    await link.waitFor({ timeout: 30000 });
    await h.hover(page.locator("div.a3s").first(), 3500);
    const href = await link.evaluate((a) => {
      const u = new URL(a.href);
      return u.hostname.includes("google.") ? u.searchParams.get("q") : a.href;
    });
    await h.to(link);
    await sleep(500);
    await page.mouse.down(); await page.mouse.up();
    await go(href);
    await page.waitForSelector(".needs");
    await h.hover(".needs", 2500);
    const picks = page.locator(".pick");
    const n = await picks.count();
    for (let i = 0; i < n; i++) {
      const label = await picks.nth(i).locator(".pick__label").innerText();
      await h.to(picks.nth(i));
      await sleep(350);
      await picks.nth(i).locator("input").setInputFiles(
        path.join(DOCS, "tana", label.includes("TIN") ? "tin_certificate.pdf" : "business_license_renewed.pdf"));
      await sleep(600);
    }
    await h.click('button:has-text("Send documents")');
    await page.waitForSelector("text=we have it", { timeout: 60000 });
    await sleep(1200);
  },
  async S08() {
    await openMerchant("Tana Spice");
    await h.hover(".trail", 2000);
    await waitStatus("Tana Spice", ["ready", "needs_attention", "awaiting_merchant"]);
    await sleep(4500);
    await h.hover(".ws-head .seal", 1800);
    await h.scrollTo(".memo", { offset: 110 });
    await h.drift(2500);
  },
  async S09(t) {
    await go(`${GH}/actions/workflows/daily-routine.yml`);
    await h.hover("main h1, main h2", 1800);
    execFile("gh", ["workflow", "run", "daily-routine.yml", "-R", "abeni-al7/ai-agent"], () => {});
    await sleep(9000);
    await page.reload({ waitUntil: "domcontentloaded" });
    await capture(page);
    await sleep(1500);
    await h.hover('a:has-text("Wekil morning routine") >> nth=1', 2500).catch(() => {});
    await h.drift(Math.max(2000, t - 16000));
  },
  async S10() {
    await go(APP);
    const end = Date.now() + 240000;
    while (Date.now() < end && (await page.locator(".case--rescreen_hit").count()) === 0) await sleep(3000);
    await sleep(1500);
    await h.scrollTo("#cases", { offset: 120 });
    await h.hover(".case--rescreen_hit", 4000).catch(() => {});
    await h.hover(".case--renewal", 4000).catch(() => {});
    await h.hover(".case--overdue", 3500).catch(() => {});
    await go("https://mail.google.com/mail/u/0/#search/subject%3A%22Wekil+digest%22");
    await page.waitForSelector("tr.zA", { timeout: 60000 });
    await sleep(800);
    await h.click(page.locator("tr.zA").first());
    await h.hover(page.locator("div.a3s").first(), 6000);
  },
  async S11() {
    await go(APP);
    await h.type("#command", "Who has been waiting on merchants for more than 3 days? Chase them.", { fast: true });
    await h.click('.command__form button[type="submit"]');
    await page.waitForSelector(".command__answer", { timeout: 120000 });
    await sleep(1200);
    await h.hover(".command__answer", 3000);
    if (await page.locator(".plan").count()) {
      await h.hover(".plan ol", 2500);
      await h.click('button:has-text("Confirm and send")');
      await page.waitForSelector(".done", { timeout: 60000 }).catch(() => {});
      await h.hover(".done", 2500).catch(() => {});
    }
  },
  async S12() {
    for (const [f, needle] of [["backend/src/wekil/workflow.py", "def _review"], ["backend/src/wekil/tools/gemini.py", "def call"],
      ["backend/src/wekil/tools/screening.py", "def name_score"], ["backend/src/wekil/commands.py", "WRITE_TOOLS ="],
      ["backend/src/wekil/routine.py", "def run("], [".github/workflows/daily-routine.yml", "schedule:"]]) {
      await showCode(f, needle, 5600);
    }
  },
  async S13() {
    for (const [f, needle] of [["frontend/src/console/Workspace.tsx", "export function WorkspacePage"],
      ["frontend/src/Seal.tsx", "function rosette"], ["frontend/src/portal/Apply.tsx", "export function ApplyPage"]]) {
      await showCode(f, needle, 6500);
    }
  },
  async S14(t) {
    await go(APP);
    await page.waitForSelector(".page-head h1");
    await h.hover(".page-head h1", 2000);
    await h.drift(t - 3500);
  },
};

// ---------- run ----------
const log = [];
capturing = true;
const t0 = Date.now();
await sleep(600);
for (const id of Object.keys(SCENES)) {
  if (ONLY.size && !ONLY.has(id)) continue;
  const target = (TIMING[id] ?? 5) * 1000 + 600; // narration plus a breath
  const start = Date.now();
  log.push({ id, start: (start - t0) / 1000 });
  process.stdout.write(`${id} target ${(target / 1000).toFixed(1)}s ... `);
  try {
    await SCENES[id](target);
  } catch (e) {
    console.log("\n  scene error:", e.message.split("\n")[0]);
    await page.screenshot({ path: path.join(OUT, `${id}-error.png`) }).catch(() => {});
  }
  const left = target - (Date.now() - start);
  if (left > 0) await h.drift(left);
  log.at(-1).end = (Date.now() - t0) / 1000;
  console.log(`took ${(log.at(-1).end - log.at(-1).start).toFixed(1)}s`);
}
await sleep(800);
capturing = false;
const tEnd = Date.now();
await ctx.close();

// Frames -> constant 30 fps H.264, timed exactly as captured.
const list = frames.map(([f, ts], i) => `file 'frames/${f}'\nduration ${(((frames[i + 1]?.[1] ?? tEnd) - ts) / 1000).toFixed(4)}`);
list.push(`file 'frames/${frames.at(-1)[0]}'`);
fs.writeFileSync(path.join(OUT, "frames.txt"), list.join("\n"));
const firstOffset = (frames[0][1] - t0) / 1000;
fs.writeFileSync(path.join(OUT, "scenes.json"), JSON.stringify(log.map((s) => ({ ...s, start: s.start - firstOffset, end: s.end - firstOffset })), null, 1));
execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", path.join(OUT, "frames.txt"),
  "-vf", "scale=1920:1080:flags=lanczos,fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "17", "-preset", "slow",
  path.join(OUT, "video.mp4")]);
console.log("video:", path.join(OUT, "video.mp4"));
