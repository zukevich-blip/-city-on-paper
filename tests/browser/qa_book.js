// Browser QA for book/: cover → contents → country → city → plate → next, phone and desktop.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/qa_book.js http://127.0.0.1:8765/book/
const { chromium } = require("playwright");
const base = process.argv[2];
if (!base) throw Error("Usage: qa_book.js <url of book/>");
const results = [];
const check = (name, ok, detail = "") => { results.push(ok); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail}`); };
const views = [
  { name: "iphone-390", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
  { name: "iphone-320", viewport: { width: 320, height: 640 }, isMobile: true, hasTouch: true },
  { name: "desktop-1280", viewport: { width: 1280, height: 900 } },
];
(async () => {
  const browser = await chromium.launch();
  for (const v of views) {
    const ctx = await browser.newContext(v);
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(String(e)));
    page.on("console", m => { if (m.type() === "error" && !/ERR_|tile\.|wikimedia/.test(m.text())) errors.push(m.text()); });
    await page.route(/tile\.openstreetmap\.org|thumb\.wikimedia\.org|upload\.wikimedia\.org/, r => r.abort());
    await page.goto(base, { waitUntil: "networkidle" });
    await page.waitForSelector(".toc li");
    check(`${v.name}: cover with one h1, preface, featured strip and contents`,
      (await page.locator("h1").count()) === 1 && (await page.locator(".preface").count()) === 1 &&
      (await page.locator(".feat").count()) >= 6 && (await page.locator(".toc li").count()) >= 8);
    check(`${v.name}: contents give numbers (cities, views)`, /город/.test(await page.locator(".toc li").first().innerText()) && /вид/.test(await page.locator(".toc li").first().innerText()));
    const noScroll = () => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
    check(`${v.name}: no horizontal scroll on cover`, await noScroll());
    await page.locator(".toc a").nth(1).click();
    await page.waitForSelector(".card");
    check(`${v.name}: country page lists cities with counts`, (await page.locator(".card").count()) >= 2 && /вид/.test(await page.locator(".card .meta").first().innerText()));
    await page.goto(base + "#/city/rim", { waitUntil: "networkidle" });
    await page.waitForSelector(".pl");
    check(`${v.name}: edited chapter shows three views, each with a question and a hidden answer`,
      (await page.locator(".view").count()) === 3 && (await page.locator(".view .q").count()) === 3 &&
      (await page.locator(".view details.ans[open]").count()) === 0 && (await page.locator(".pl").count()) >= 6 && (await page.locator('a[href*="compare"]').count()) >= 1);
    await page.locator(".ans summary").first().click();
    check(`${v.name}: answer opens on tap`, await page.locator(".view details.ans[open]").count() === 1);
    check(`${v.name}: chapter tells what changed and which old guidebooks exist`, (await page.locator(".tl li").count()) >= 4 && (await page.locator(".bl li").count()) >= 2);
    check(`${v.name}: sheets kept by archives are counted and listed`, /у хранителей/.test(await page.locator(".counts").innerText()) && (await page.locator(".archive li").count()) >= 1);
    await page.goto(base + "#/city/florence", { waitUntil: "networkidle" });
    await page.waitForSelector(".pl");
    check(`${v.name}: other cities still show stars and a grid`, (await page.locator(".strip .feat").count()) >= 3 && (await page.locator(".pl").count()) >= 6);
    await page.goto(base + "#/city/rim", { waitUntil: "networkidle" });
    await page.waitForSelector(".pl");
    check(`${v.name}: no horizontal scroll on city`, await noScroll());
    await page.locator(".pl").first().click();
    await page.waitForSelector(".plate h1");
    const title = await page.locator(".plate h1").innerText();
    check(`${v.name}: plate page shows author/date/holder/rights and an original link`,
      (await page.locator(".facts li").count()) === 4 && (await page.locator('a[href^="https://"][target="_blank"]').count()) >= 1);
    const next = page.locator(".dock .btn:not(.ghost)");
    check(`${v.name}: one big "next" action under the thumb`, (await next.count()) === 1 && (await next.boundingBox()).height >= 44);
    await next.click();
    await page.waitForFunction(t => document.querySelector(".plate h1") && document.querySelector(".plate h1").innerText !== t, title);
    check(`${v.name}: next opens another plate`, true);
    await page.goto(base + "#/plate/nonexistent", { waitUntil: "networkidle" });
    check(`${v.name}: unknown page is explained, not blank`, /нет/i.test(await page.locator("main h1").first().innerText()));
    check(`${v.name}: no console/page errors`, errors.length === 0, errors.slice(0, 2).join(" | "));
    await ctx.close();
  }
  await browser.close();
  if (results.some(r => !r)) process.exit(1);
})();
