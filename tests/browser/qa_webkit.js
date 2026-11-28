// WebKit (Safari engine) smoke test of the book and the comparison. WebKit under Playwright is an engine test, not a
// physical iPhone/iPad: touch, address-bar behaviour and memory limits of real Safari stay NOT TESTED.
// Usage: node tests/browser/qa_webkit.js http://127.0.0.1:8765/
const { webkit, devices } = require("playwright");
const base = process.argv[2];
if (!base) throw Error("Usage: qa_webkit.js <site root url>");
const results = [];
const check = (name, ok, detail = "") => { results.push(ok); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail}`); };
(async () => {
  const browser = await webkit.launch();
  for (const [name, dev] of [["iPhone 13 (WebKit)", devices["iPhone 13"]], ["iPad (gen 7) (WebKit)", devices["iPad (gen 7)"]]]) {
    const ctx = await browser.newContext({ ...dev }), page = await ctx.newPage(), errs = [];
    page.on("pageerror", (e) => errs.push(String(e)));
    await page.route(/tile\.openstreetmap|wikimedia|gallica|geohistoricaldata/, (r) => r.abort());
    await page.goto(base + "book/", { waitUntil: "networkidle" });
    await page.waitForSelector(".toc li");
    check(`${name}: cover opens`, (await page.locator("h1").count()) === 1);
    await page.goto(base + "book/#/sheet/parismusees-320291945", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#zoomimg");
    await page.waitForFunction(() => document.getElementById("zoomimg").complete && document.getElementById("zoomimg").naturalWidth > 0, null, { timeout: 15000 });
    check(`${name}: sheet image loads`, true);
    await page.waitForSelector("#placemap");
    await page.locator(".layers > summary").click();
    await page.waitForFunction(() => /контур/.test(document.getElementById("layNote").textContent), null, { timeout: 15000 });
    check(`${name}: place layers open`, true);
    await page.locator(".lens > summary").click();
    await page.locator('.lensbtn[data-lens="edges"]').click();
    await page.waitForSelector(".zoomwrap canvas", { timeout: 15000 });
    check(`${name}: edge lens draws on a canvas`, true);
    check(`${name}: no horizontal scroll`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 4));
    await page.goto(base + "poc/compare/#notre-dame-benoist-carnavalet", { waitUntil: "networkidle" });
    await page.waitForFunction(() => { const b = document.getElementById("morphBox"); return b && b.dataset.pair === "notre-dame-benoist-carnavalet" && /^live-/.test(b.dataset.state || ""); }, null, { timeout: 15000 });
    await page.locator("#morphBox > summary").click();
    await page.locator("#morphT").fill("100");
    check(`${name}: local morph canvas works`, true);
    check(`${name}: no page errors`, errs.length === 0, errs.slice(0, 2).join(" | "));
    await ctx.close();
  }
  await browser.close();
  if (results.some((r) => !r)) process.exit(1);
})();
