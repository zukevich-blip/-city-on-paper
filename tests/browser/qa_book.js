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
    await page.goto(base + "#/benoist", { waitUntil: "networkidle" });
    await page.waitForSelector(".hot");
    check(`${v.name}: Benoist page explains the signature, lists cities and opens a note on tap`,
      (await page.locator(".hot").count()) === 5 && (await page.locator(".toc li").count()) >= 5);
    await page.locator(".hot").nth(3).click();
    check(`${v.name}: tapping a number reads that inscription`, /Lemercier/.test(await page.locator("#signNote").innerText()) && noScroll && (await noScroll()));
    await page.locator(".bsheets").scrollIntoViewIfNeeded();
    // lazy images load as they scroll into view: walk down the grid, then wait until every file has really loaded
    while (await page.locator("#bsMore").count()) await page.locator("#bsMore").evaluate((b) => b.click()); // layout shifts while lazy images load, so no stability wait
    for (const f of await page.locator(".bsheet").all()) await f.scrollIntoViewIfNeeded();
    await page.waitForFunction(() => [...document.querySelectorAll(".bsheet img")].every((i) => i.complete && i.naturalWidth > 500), null, { timeout: 90000 });
    const expectedSheets = await page.evaluate(async () => (await (await fetch("benoist-sheets.json")).json()).sheets.length);
    const bs = await page.locator(".bsheet").evaluateAll((a) => ({ n: a.length, ok: a.every((f) => f.querySelector("img").naturalWidth > 500),
      rights: a.every((f) => /(Public Domain Mark|CC0)/.test(f.innerText)), roles: a.every((f) => /:/.test(f.querySelector("small").innerText)) }));
    check(`${v.name}: Benoist hub shows every open museum sheet of the shipped list with rights and participants`, bs.n === expectedSheets && bs.ok && bs.rights && bs.roles, JSON.stringify(bs));
    check(`${v.name}: Benoist hub has no horizontal scroll`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 4));
    await page.goto(base + "#/sheet/parismusees-320290066", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#zoomimg");
    const w0 = await page.locator("#zoomimg").evaluate((i) => i.getBoundingClientRect().width);
    await page.locator("#zoomrange").fill("250");
    const w1 = await page.locator("#zoomimg").evaluate((i) => i.getBoundingClientRect().width);
    check(`${v.name}: sheet page zooms the whole sheet by slider and keeps the page unscrolled sideways`, w1 > w0 * 2.3 && (await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 4)), `${w0}→${w1}`);
    check(`${v.name}: sheet page names holder, rights and a next sheet`, /CC0/.test(await page.locator(".facts").innerText()) && (await page.locator(".dock .btn").count()) >= 1);
    await page.goto(base + "#/catalog", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".cwlist li");
    const stat = await page.locator(".stats dd").allInnerTexts();
    check(`${v.name}: register shows honest counters and a long list`, stat.length === 5 && Number(stat[0]) >= Number(stat[1]) && (await page.locator(".cw").count()) >= 30, stat.join("/"));
    const before = await page.locator(".cw").count();
    await page.locator(".chips").nth(1).locator("button").nth(1).click();
    check(`${v.name}: register filters narrow the list`, (await page.locator(".cw").count()) <= before);
    check(`${v.name}: register has no horizontal scroll`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 4));
    await page.goto(base + "#/places", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".toc li");
    check(`${v.name}: five place histories are listed`, (await page.locator(".toc li").count()) === 5);
    await page.goto(base + "#/place/tuileries", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".story li");
    check(`${v.name}: lost Tuileries says plainly that no same-view photo can exist`, /не существует/.test(await page.locator("[role=note]").innerText()));
    const facts = await page.locator(".story li").evaluateAll((a) => a.map((li) => ({ when: li.querySelector(".when").innerText, href: li.querySelector("a.src").href })));
    check(`${v.name}: every story fact has a date and an https source`, facts.length >= 3 && facts.every((f) => f.when && /^https:/.test(f.href)), JSON.stringify(facts.slice(0, 1)));
    check(`${v.name}: unknowns are stated`, (await page.locator(".unk li").count()) >= 1);
    check(`${v.name}: place page has no horizontal scroll`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 4));
    check(`${v.name}: place page mounts map, compare link and 1878 plan preview`,
      (await page.locator("#lmap").count()) === 1 && (await page.locator('a[href*="../poc/compare/?journey=1#tuileries-"]').count()) === 1 && (await page.locator(".plan-box").count()) === 1);
    await page.goto(base + "#/sheet/parismusees-320291945", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#zoomimg");
    check(`${v.name}: sheet cross-links to its place story and ready comparison`,
      (await page.locator('a[href="#/place/notre-dame"]').count()) === 1 && (await page.locator('a[href*="../poc/compare/?journey=1#notre-dame-"]').count()) === 1);
    await page.goto(base + "#/city/antverpen", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("h1");
    check(`${v.name}: zero-plate city from omitted country renders without crashing`,
      /Антверпен/i.test(await page.locator("main h1").first().innerText()) && (await page.locator(".nolook").count()) === 1);
    await page.goto(base + "#/plate/nonexistent", { waitUntil: "networkidle" });
    check(`${v.name}: unknown page is explained, not blank`, /нет/i.test(await page.locator("main h1").first().innerText()));
    check(`${v.name}: no console/page errors`, errors.length === 0, errors.slice(0, 2).join(" | "));
    await ctx.close();
  }
  await browser.close();
  if (results.some(r => !r)) process.exit(1);
})();
