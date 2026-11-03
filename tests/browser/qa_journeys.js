// Visual and interaction QA for City on Paper: Era Journeys.
const { chromium } = require("playwright");
const fs = require("fs");
const [, , url, outDir] = process.argv;
if (!url || !outDir) throw Error("Usage: node qa_journeys.js <url> <screenshot-directory>");
fs.mkdirSync(outDir, { recursive: true });
const viewports = [
  { name: "iphone-375", width: 375, height: 812, mobile: true },
  { name: "iphone-390", width: 390, height: 844, mobile: true },
  { name: "ipad-820", width: 820, height: 1180, mobile: true },
  { name: "desktop-1440", width: 1440, height: 900, mobile: false },
];
async function run() {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  const check = (description, valid) => {
    results.push({ description, pass: !!valid });
    console.log((valid ? "PASS " : "FAIL ") + description);
  };
  try {
    for (const vp of viewports) {
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        isMobile: vp.mobile, hasTouch: vp.mobile,
      });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", e => errors.push(String(e)));
      page.on("response", r => { if (r.url().includes("/data/curation/") && !r.ok()) errors.push("Catalog HTTP " + r.status()); });
      await page.goto(url, { waitUntil: "domcontentloaded" });
      await page.waitForFunction(() => document.querySelectorAll("#cards .card").length === 56);
      check(vp.name + " initial 56 museum-backed records", await page.locator("#cards .card").count() === 56);
      check(vp.name + " no horizontal scrolling", await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
      check(vp.name + " images exist", await page.evaluate(() =>
        [...document.querySelectorAll(".heroVisual img")].every(el => el.complete && el.naturalWidth > 0)));
      await page.locator('[data-era="17"]').click();
      check(vp.name + " XVII century shows two records", await page.locator("#cards .card").count() === 2);
      await page.locator('[data-era="18"]').click();
      check(vp.name + " XVIII century expands with historic prints", await page.locator("#cards .card").count() >= 15);
      await page.locator('[data-era="21"]').click();
      check(vp.name + " XXI century shows one record", await page.locator("#cards .card").count() === 1);
      await page.locator('[data-era="all"]').click();
      await page.locator("#query").fill("Мадлен");
      check(vp.name + " full-text search finds Madeleine", await page.locator("#cards .card").count() >= 1);
      await page.locator("#reset").click();
      await page.locator("#cards .card").first().locator(".textBtn").click();
      check(vp.name + " details dialog accessible", await page.locator("dialog[open] #detailTitle").isVisible());
      await page.locator("#closeDetail").click();
      await page.locator("#cards .card").first().locator(".fav").click();
      await page.locator("#savedOnly").click();
      check(vp.name + " collector saves favorite", await page.locator("#cards .card").count() === 1);
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForFunction(() => document.querySelectorAll("#cards .card").length === 56);
      await page.locator("#savedOnly").click();
      check(vp.name + " favorite persisted", await page.locator("#cards .card").count() === 1);
      await page.locator("#export").click();
      // The export button must be wired without a page exception.
      await page.locator("#savedOnly").click();
      await page.locator('[data-route="rome"]').click();
      check(vp.name + " city route filters cards", await page.locator("#cards .card").count() >= 9);
      await page.locator("#reset").click();
      await page.locator("#withImages").click();
      check(vp.name + " image-only filter shows artworks", await page.locator("#cards .card").count() >= 40);
      await page.locator("#reset").click();
      await page.locator("#technique").selectOption("Литография");
      check(vp.name + " technique filter picks lithographs", await page.locator("#cards .card").count() >= 10);
      await page.locator("#reset").click();
      await page.locator("#cards .artLink").first().click();
      check(vp.name + " zoom displays museum art", await page.locator("#zoomDialog[open] #zoomImage").isVisible());
      await page.locator("#zoomScale").evaluate(e => { e.value="150"; e.dispatchEvent(new Event("input", { bubbles: true })); });
      check(vp.name + " zoom scale works", await page.locator("#zoomImage").evaluate(e => e.style.width === "150%"));
      await page.locator("#zoomClose").click();
      await page.locator("#cards .card .textBtn").first().click();
      check(vp.name + " provenance card links original institution", await page.locator("#detailLinks a").count() >= 1);
      await page.locator("#closeDetail").click();
      check(vp.name + " no JS runtime errors", errors.length === 0);
      await page.locator("#reset").click();
      // Full-resolution QA screenshot capped to 12 cards: 56 cards on a phone would exceed browser texture limits.
      await page.evaluate(() => { [...document.querySelectorAll("#cards .card")].slice(12).forEach(e=>{e.style.display="none";}); });
      await page.screenshot({ path: outDir + "/" + vp.name + "-atlas.jpg", type: "jpeg", quality: 70, fullPage: true });
      await page.locator("#salon").screenshot({ path: outDir + "/" + vp.name + "-museum-salon.jpg", type: "jpeg", quality: 75 });
      await context.close();
    }
  } finally { await browser.close(); }
  fs.writeFileSync(outDir + "/qa-journeys.json", JSON.stringify(results, null, 2));
  if (results.some(x => !x.pass)) process.exitCode = 1;
}
run().catch(e => { console.error(e); process.exitCode = 1; });
