// Touch-gesture regression for poc/compare (iPhone 390 emulation, CDP touch events).
// Usage: NODE_PATH=$(npm root -g) node tests/browser/qa_compare_touch.js http://127.0.0.1:8766/poc/compare/#madeleine-ph-benoist
// Expect: curtainJumped=false, zoomed panned=true & curtainMoved=false, handle drags move=true, tap-to-jump ok=true.
const { chromium } = require("playwright");
const url = process.argv[2] || "http://127.0.0.1:8766/poc/compare/#madeleine-ph-benoist";
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  await p.goto(url, { waitUntil: "networkidle" });
  await p.waitForTimeout(800);
  const cdp = await ctx.newCDPSession(p);
  const state = () => p.evaluate(() => ({ split: +document.getElementById("handle").getAttribute("aria-valuenow"), scroll: Math.round(document.getElementById("zoomwrap").scrollLeft), pageY: Math.round(scrollY) }));
  async function swipe(x0, y0, x1, y1) {
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: x0, y: y0 }] });
    for (let i = 1; i <= 12; i++) { await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: x0 + (x1 - x0) * i / 12, y: y0 + (y1 - y0) * i / 12 }] }); await p.waitForTimeout(16); }
    await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await p.waitForTimeout(400);
  }
  await p.evaluate(() => document.getElementById("stage").scrollIntoView({block:"start"})); await p.waitForTimeout(200);
  const st = await p.locator("#stage").boundingBox();
  const y = st.y + st.height * 0.6;
  const s0 = await state();
  await swipe(st.x + st.width * 0.85, y, st.x + st.width * 0.85, y - 150);
  const s1 = await state();
  console.log("vertical-scroll-on-image", JSON.stringify({ before: s0, after: s1, curtainJumped: s0.split !== s1.split }));
  { await p.evaluate(() => document.getElementById("stage").scrollIntoView({block:"start"})); await p.waitForTimeout(200);
    const hb = await p.locator("#handle").boundingBox(); const a = await state();
    await swipe(hb.x + hb.width/2, hb.y + 80, hb.x + hb.width/2 - 100, hb.y + 80); const c = await state();
    console.log("unzoomed-handle-drag", JSON.stringify({ before: a.split, after: c.split, moved: a.split !== c.split }));
    await p.touchscreen.tap(st.x + st.width*0.8, st.y + 60); await p.waitForTimeout(200); const d = await state();
    console.log("tap-to-jump", JSON.stringify({ after: d.split, ok: Math.abs(d.split-80) <= 2 })); }
  await p.click("#zoomBtn"); await p.waitForTimeout(300);
  await p.evaluate(() => document.getElementById("zoomwrap").scrollIntoView({block:"start"})); await p.waitForTimeout(200);
  await p.evaluate(() => { document.getElementById("zoomwrap").scrollLeft = 0; }); await p.waitForTimeout(100);
  const zw = await p.locator("#zoomwrap").boundingBox();
  const z0 = await state();
  await swipe(zw.x + zw.width * 0.9, zw.y + 120, zw.x + zw.width * 0.15, zw.y + 120);
  const z1 = await state();
  console.log("zoomed-horizontal-swipe", JSON.stringify({ before: z0, after: z1, panned: z1.scroll > z0.scroll, curtainMoved: z0.split !== z1.split }));
  await p.evaluate(() => { const zw = document.getElementById("zoomwrap"); zw.scrollLeft = zw.scrollWidth * (+document.getElementById("handle").getAttribute("aria-valuenow"))/100 - zw.clientWidth/2; }); await p.waitForTimeout(200);
  const hb = await p.locator("#handle").boundingBox(); console.log("handle-x-in-viewport", Math.round(hb.x), "viewport 390");
  const h0 = await state();
  await swipe(hb.x + hb.width / 2, hb.y + 60, hb.x + hb.width / 2 - 80, hb.y + 60);
  const h1 = await state();
  console.log("handle-drag", JSON.stringify({ before: h0.split, after: h1.split, moved: h0.split !== h1.split }));
  await b.close();
})().catch(e => { console.error("ERR", e.message.split("\n")[0]); process.exit(1); });
