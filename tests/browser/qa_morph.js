// Morph gate in the compare tool: offered only when the control points justify it, never forced.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/qa_morph.js http://127.0.0.1:8765/poc/compare/
const { chromium } = require("playwright");
const base = process.argv[2];
if (!base) throw Error("Usage: qa_morph.js <url of poc/compare/>");
const results = [];
const check = (name, ok, detail = "") => { results.push(ok); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail}`); };
(async () => {
  const browser = await chromium.launch();
  for (const v of [{ name: "iphone-390", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }, { name: "desktop-1280", viewport: { width: 1280, height: 900 } }]) {
    const ctx = await browser.newContext(v), page = await ctx.newPage(), errs = [];
    page.on("pageerror", (e) => errs.push(String(e)));
    await page.goto(base + "#synthetic-near-identical", { waitUntil: "networkidle" });
    await page.waitForSelector("#morphBox");
    await page.locator("#morphBox > summary").click();
    await page.waitForSelector("#morphLive:not([hidden])", { timeout: 8000 });
    await page.locator("#morphT").fill("50");
    const painted = await page.locator("#morphCv").evaluate((c) => { const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4000) if (d[i] > 0) n++; return n; });
    check(`${v.name}: passing pair morphs and paints the canvas`, painted > 50 && /50%/.test(await page.locator("#morphTv").innerText()), String(painted));
    for (const id of ["notre-dame-benoist-carnavalet", "madeleine-benoist-carnavalet", "louvre-colonnade-benoist-carnavalet"]) {
      await page.goto(base + "#" + id, { waitUntil: "networkidle" });
      await page.waitForFunction(() => document.getElementById("morphWhy").textContent.length > 0, null, { timeout: 8000 });
      await page.waitForSelector("#morphLive:not([hidden])", { timeout: 8000 });
      const why = await page.locator("#morphWhy").innerText();
      await page.locator("#morphT").fill("100");
      const full = await page.locator("#morphCv").evaluate((c) => { const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4000) if (d[i] > 0) n++; return n; });
      await page.locator("#morphT").fill("0");
      const zero = await page.locator("#morphCv").evaluate((c) => c.toDataURL().length);
      await page.locator("#morphT").fill("100");
      const one = await page.locator("#morphCv").evaluate((c) => c.toDataURL().length);
      check(`${v.name}: real pair ${id} has a local morph that changes the picture and says it is local`, /Местное/.test(why) && full > 50 && zero !== one, why.slice(0, 60));
    }
    await page.goto(base + "#madeleine-ph-benoist", { waitUntil: "networkidle" });
    await page.waitForFunction(() => /недоступно/.test(document.getElementById("morphWhy").textContent), null, { timeout: 8000 });
    check(`${v.name}: a pair over the error limits is refused with the numbers`, /допустимо/.test(await page.locator("#morphWhy").innerText()) && (await page.locator("#morphLive").isHidden()));
    check(`${v.name}: no horizontal scroll`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 4));
    check(`${v.name}: no page errors`, errs.length === 0, errs.join("|"));
    await ctx.close();
  }
  await browser.close();
  if (results.some((r) => !r)) process.exit(1);
})();
