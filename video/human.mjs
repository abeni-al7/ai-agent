// Human-paced input and a drawn cursor for recorded browser sessions.

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rand = (a, b) => a + Math.random() * (b - a);

// Drawn cursor (the headless screencast does not paint the OS pointer). Follows real mouse events.
export const CURSOR_SCRIPT = `
(() => {
  if (window.__wkCursor) return; window.__wkCursor = true;
  const make = () => {
    const c = document.createElement('div');
    c.id = '__cursor';
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2.5 L4 19 L8.6 14.9 L11.6 21.4 L14.4 20.1 L11.4 13.7 L17.6 13.5 Z" fill="#111" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:2147483647, pointerEvents:'none',
      transform:'translate(-200px,-200px)', filter:'drop-shadow(0 1px 1.5px rgba(0,0,0,.35))'});
    document.documentElement.appendChild(c);
    const pos = JSON.parse(sessionStorage.getItem('__cursorPos') || 'null');
    if (pos) c.style.transform = 'translate(' + (pos[0]-3) + 'px,' + (pos[1]-2) + 'px)';
    return c;
  };
  let c = null;
  const ensure = () => { if (!c || !c.isConnected) c = make(); return c; };
  document.addEventListener('mousemove', (e) => {
    ensure().style.transform = 'translate(' + (e.clientX-3) + 'px,' + (e.clientY-2) + 'px)';
    try { sessionStorage.setItem('__cursorPos', JSON.stringify([e.clientX, e.clientY])); } catch {}
  }, true);
  document.addEventListener('mousedown', (e) => {
    const r = document.createElement('div');
    Object.assign(r.style, {position:'fixed', left:(e.clientX-14)+'px', top:(e.clientY-14)+'px', width:'28px', height:'28px',
      borderRadius:'50%', border:'2px solid rgba(35,65,124,.55)', zIndex:2147483646, pointerEvents:'none',
      transition:'transform 380ms ease-out, opacity 380ms ease-out'});
    document.documentElement.appendChild(r);
    requestAnimationFrame(() => { r.style.transform = 'scale(1.7)'; r.style.opacity = '0'; });
    setTimeout(() => r.remove(), 420);
  }, true);
  if (document.readyState !== 'loading') ensure(); else document.addEventListener('DOMContentLoaded', ensure);
})();`;

export class Human {
  constructor(page) {
    this.page = page;
    this.x = 800;
    this.y = 450;
  }

  async move(x, y, ms) {
    const { page } = this;
    const dx = x - this.x, dy = y - this.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 2) return;
    ms = ms ?? Math.min(1100, 260 + dist * 0.55) * rand(0.9, 1.15);
    // Curved path: one control point pushed sideways, eased in and out.
    const nx = -dy / (dist || 1), ny = dx / (dist || 1), bend = rand(-0.18, 0.18) * dist;
    const cx = this.x + dx * 0.5 + nx * bend, cy = this.y + dy * 0.5 + ny * bend;
    const steps = Math.max(8, Math.round(ms / 16));
    const x0 = this.x, y0 = this.y;
    for (let i = 1; i <= steps; i++) {
      const t = i / steps, e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      const px = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * cx + e * e * x;
      const py = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * cy + e * e * y;
      await page.mouse.move(px, py);
      await sleep(ms / steps);
    }
    this.x = x; this.y = y;
  }

  async to(locator, { dx = 0.5, dy = 0.5 } = {}) {
    const loc = typeof locator === "string" ? this.page.locator(locator).first() : locator;
    await loc.scrollIntoViewIfNeeded({ timeout: 15000 }).catch(() => {});
    const b = await loc.boundingBox({ timeout: 15000 });
    if (!b) throw new Error("no box for " + locator);
    const x = b.x + b.width * Math.min(0.85, Math.max(0.15, dx + rand(-0.08, 0.08)));
    const y = b.y + b.height * Math.min(0.8, Math.max(0.2, dy + rand(-0.1, 0.1)));
    await this.move(x, y);
    return loc;
  }

  async click(locator, opts = {}) {
    const loc = await this.to(locator, opts);
    await sleep(rand(120, 260));
    await this.page.mouse.down();
    await sleep(rand(60, 110));
    await this.page.mouse.up();
    await sleep(rand(200, 380));
    return loc;
  }

  async type(locator, text, { fast = false } = {}) {
    await this.click(locator);
    for (const ch of text) {
      await this.page.keyboard.type(ch);
      await sleep(fast ? rand(28, 70) : rand(55, 135) + (ch === " " ? rand(20, 90) : 0));
    }
    await sleep(rand(150, 300));
  }

  async hover(locator, ms = 900) {
    await this.to(locator);
    await sleep(ms);
  }

  /** Smooth wheel scroll so the reader can follow. */
  async scroll(pixels, ms = 1400) {
    const steps = Math.max(10, Math.round(ms / 24));
    let done = 0;
    for (let i = 1; i <= steps; i++) {
      const t = i / steps, e = 1 - Math.pow(1 - t, 3);
      const target = Math.round(pixels * e);
      await this.page.mouse.wheel(0, target - done);
      done = target;
      await sleep(ms / steps);
    }
  }

  /** Scroll until the element's top sits near the top third of the viewport. */
  async scrollTo(locator, { offset = 140, ms } = {}) {
    const loc = typeof locator === "string" ? this.page.locator(locator).first() : locator;
    await loc.waitFor({ timeout: 20000 });
    const top = await loc.evaluate((el) => el.getBoundingClientRect().top);
    const delta = top - offset;
    if (Math.abs(delta) > 4) await this.scroll(delta, ms ?? Math.min(2200, 500 + Math.abs(delta) * 0.6));
    await sleep(250);
  }

  async drift(ms) {
    // Small idle movements while the narration runs.
    const end = Date.now() + ms;
    while (Date.now() < end - 900) {
      await this.move(this.x + rand(-60, 60), this.y + rand(-30, 30), rand(500, 900));
      await sleep(Math.min(end - Date.now(), rand(900, 1800)));
    }
    await sleep(Math.max(0, end - Date.now()));
  }
}
