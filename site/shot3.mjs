import { chromium } from 'playwright';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 950 }, deviceScaleFactor: 1 });
for (const [url, out] of [['https://crucible-weld.vercel.app/agents/', '/tmp/shots/agents.png'],
                          ['https://crucible-weld.vercel.app/instrument/', '/tmp/shots/instrument.png']]) {
  await p.goto(url, { waitUntil: 'networkidle' });
  await p.evaluate(() => document.querySelectorAll('[data-reveal]').forEach(e => e.classList.add('in')));
  await p.waitForTimeout(1200);
  await p.screenshot({ path: out });
}
await b.close(); console.log('ok');
