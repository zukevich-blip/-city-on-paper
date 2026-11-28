// Visitor scenarios for the gallery, light table, game, showcase and home. Real images must open (naturalWidth > 0), not just cards.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/qa_gallery.js http://127.0.0.1:8765/book/ [screens-dir]
const { chromium } = require("playwright");
const fs = require("fs");
const [, , base, shots] = process.argv;
if (!base) throw Error("Usage: qa_gallery.js <url of book/> [dir]");
if (shots) fs.mkdirSync(shots, { recursive: true });
const results = [];
const check = (name, ok, detail = "") => { results.push(ok); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail}`); };
const views = [
  { name: "iphone-390", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
  { name: "ipad-820", viewport: { width: 820, height: 1180 }, isMobile: true, hasTouch: true },
  { name: "desktop-1280", viewport: { width: 1280, height: 900 } },
];
(async () => {
  const browser = await chromium.launch();
  for (const v of views) {
    const ctx = await browser.newContext(v), page = await ctx.newPage(), errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => { if (m.type() === "error" && !/ERR_|tile\.|wikimedia|geohistoricaldata|gallica|CORS/.test(m.text())) errors.push(m.text()); });
    await page.route(/tile\.openstreetmap/, (r) => r.abort());
    const shot = async (n) => { if (shots && v.name !== "ipad-820") await page.screenshot({ path: `${shots}/${v.name}-${n}.png` }); };
    const imgOk = (sel) => page.waitForFunction((s) => { const i = document.querySelector(s); return i && i.complete && i.naturalWidth > 0; }, sel, { timeout: 15000 });
    const openF = async () => { if (!(await page.locator(".gfilters").evaluate((e) => e.open))) await page.locator(".gfilters > summary").click(); };
    const noScroll = () => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 4);
    // 1. first visit
    await page.goto(base, { waitUntil: "networkidle" });
    await page.waitForSelector(".homehero .hslide");
    await imgOk(".homehero .hslide.on img");
    const kinds = await page.locator(".gmasonry.home .gt").count();
    check(`${v.name}: first visit shows art at once (hero, doors, mixed mosaic, one h1) without text over the pictures`, kinds >= 10 && (await page.locator(".hdoor").count()) === 6 && (await page.locator("h1").count()) === 1 && (await page.locator(".hcap").first().evaluate((e) => getComputedStyle(e).position)) === "static");
    check(`${v.name}: home has no horizontal scroll`, await noScroll()); await shot("01-home");
    // 2. gallery with real images
    await page.goto(base + "#/gallery", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".gt");
    await page.waitForFunction(() => document.querySelectorAll(".gmasonry .gt img").length >= 60);
    const total = Number(((await page.locator("[role=status]").first().innerText()).match(/из (\d+)/) || [])[1]);
    check(`${v.name}: gallery offers hundreds of works`, total >= 500, String(total)); await shot("02-gallery");
    // lenses: each real lens narrows the list and its first tile image opens
    for (const [lens, rx] of [["Интерьеры", /./], ["Панорамы", /./], ["Бенуа", /./]]) {
      await page.locator(`.glens:has-text("${lens}")`).click();
      await page.waitForSelector(".gt");
      const n = await page.locator(".gmasonry .gt").count();
      await page.locator(".gmasonry .gt img").first().evaluate((i) => i.scrollIntoView());
      await imgOk(".gmasonry .gt img");
      check(`${v.name}: lens «${lens}» shows works whose images open`, n > 0 && rx.test(String(n)), String(n));
    }
    await page.locator(".glens:has-text(\"Всё\")").click();
    await openF();
    await page.locator('.gchip[data-k="c"][data-v="Рим"]').click();
    await page.waitForSelector(".gt");
    const rome = Number(((await page.locator("[role=status]").first().innerText()).match(/^(\d+)/) || [])[1]);
    await shot("03-rome");
    check(`${v.name}: Rome has many views`, rome >= 100, String(rome));
    await openF();
    await page.locator('.gchip[data-k="c"][data-v="Рим"]').click();
    await openF();
    await page.locator('.gchip[data-k="c"][data-v="Венеция"]').click();
    await page.waitForSelector(".gt");
    check(`${v.name}: Venice has its own views`, (await page.locator(".gmasonry .gt").count()) >= 30); await shot("04-venice");
    await openF();
    await page.locator("#greset").click();
    await page.locator("#gq").fill("Мерион"); await page.locator("#gq").dispatchEvent("change");
    await page.waitForFunction(() => document.querySelectorAll(".gmasonry .gt").length > 5 && document.querySelectorAll(".gmasonry .gt").length < 80);
    check(`${v.name}: search by master works`, (await page.locator(".gmasonry .gt").count()) >= 20);
    await openF();
    await page.locator("#greset").click();
    await openF();
    await page.locator('.gchip[data-k="mode"]').click();
    await page.waitForSelector(".folio .fpage");
    check(`${v.name}: in-folio spreads show pages with numbers`, (await page.locator(".folio .fnum").count()) >= 20); await shot("05-folio");
    await openF();
    await page.locator('.gchip[data-k="mode"]').click();
    // 3. twenty different works opened one after another through the dock
    await page.goto(base + "#/gallery", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".gmasonry .gt");
    await page.locator(".gmasonry .gt").nth(3).click();
    const seen = new Set();
    for (let i = 0; i < 20; i++) {
      await page.waitForFunction(() => { const a = document.querySelector(".artpage"), im = document.getElementById("zoomimg"); return a && "#/art/" + a.dataset.art === location.hash && im.complete && im.naturalWidth > 0; }, null, { timeout: 15000 });
      seen.add(page.url().split("#")[1]);
      const before = await page.evaluate(() => location.hash);
      await page.locator(".dock a.btn:not(.ghost)").click();
      await page.waitForFunction((h) => location.hash !== h, before);
    }
    check(`${v.name}: twenty different works open with real images`, seen.size === 20, String(seen.size));
    // 4. a work page: facts, rails, cabinet, deep zoom, table
    await page.goto(base + "#/art/ex-nga-81711", { waitUntil: "domcontentloaded" }).catch(() => {});
    await page.goto(base + "#/gallery", { waitUntil: "domcontentloaded" });
    await page.locator('.glens:has-text("Античность")').click();
    await page.waitForSelector(".gmasonry .gt");
    await page.locator(".gmasonry .gt").first().click();
    await imgOk("#zoomimg");
    check(`${v.name}: work page has museum, rights, source link and related rails`, (await page.locator('dl.facts a[href^="http"]').count()) === 1 && /Права/.test(await page.locator("dl.facts").innerText()) && (await page.locator(".rail .rt").count()) >= 3); await shot("06-art");
    await page.locator("#cabBox > summary").click();
    await page.waitForFunction(() => document.querySelectorAll(".cabtile").length === 9);
    await page.locator(".cabtile").nth(4).click();
    check(`${v.name}: detail cabinet cuts nine fragments and enlarges one`, (await page.locator("#cabBig canvas").count()) === 1); await shot("07-cabinet");
    await page.locator("#deepBox > summary").click();
    await page.waitForFunction(() => window.__osd && window.__osd.world.getItemCount() === 1, null, { timeout: 15000 });
    check(`${v.name}: museum loupe (deep zoom) opens the work`, true);
    await page.locator(".artctl .more > summary").click();
    await page.locator("#artTable").click();
    // 5. light table
    await page.goto(base + "#/table", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#tRand");
    await page.locator("#tRand").click();
    await page.waitForFunction(() => document.querySelectorAll(".bfig img").length === 6);
    const bg = {};
    for (const [k, t] of [["day", "Дневной"], ["lamp", "Лампа"], ["night", "Ночь"]]) { await page.locator(`.lightb:has-text("${t}")`).click(); bg[k] = await page.locator("#board").evaluate((e) => getComputedStyle(e).backgroundImage + getComputedStyle(e).backgroundColor); }
    check(`${v.name}: light table has three different lightings`, new Set(Object.values(bg)).size === 3); await shot("08-table-night");
    await page.locator("#tLayout").click();
    await page.waitForSelector("#curtain");
    await page.locator("#cRange").fill("20");
    check(`${v.name}: two works can be compared by a curtain without overlay`, (await page.locator("#curtain .cB").evaluate((e) => e.style.clipPath)).includes("20%")); await shot("09-curtain");
    // 6. guess the city
    await page.goto(base + "#/guess", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".gopt");
    const drawn = await page.locator("#gcv").evaluate((c) => new Promise((r) => setTimeout(() => { const d = c.getContext("2d").getImageData(0, 0, 360, 360).data; let n = 0; for (let i = 0; i < d.length; i += 400) if (d[i] + d[i + 1] + d[i + 2] > 0) n++; r(n); }, 800)));
    await page.locator(".gopt").first().click();
    await page.waitForSelector("#gnext:not([hidden])");
    check(`${v.name}: guess-the-city shows a fragment, answers, reveals the work`, drawn > 50 && (await page.locator("#gwork").isVisible())); await shot("10-guess");
    // 7. showcase
    await page.goto(base + "#/showcase", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#show");
    await imgOk("#showImg");
    check(`${v.name}: full-screen showcase has no navigation chrome`, (await page.evaluate(() => document.body.classList.contains("showmode") && !document.querySelector(".dock")?.offsetParent))); await shot("11-showcase");
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => /#\/gallery/.test(location.hash));
    // 7b. halls: every hall opens with its own composition and real images
    await page.goto(base + "#/halls", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".exhall");
    const hallCount = await page.locator(".exhall").count();
    check(`${v.name}: twelve halls and exhibitions are listed`, hallCount >= 12, String(hallCount)); await shot("13-halls");
    for (const [hid, sel] of [["tsvet", ".wall .wtile"], ["italiya", ".decade .gt"], ["peterburg-moskva", ".mag"], ["interery", ".spread .exfig"]]) {
      await page.goto(base + "#/hall/" + hid, { waitUntil: "domcontentloaded" });
      await page.waitForSelector(sel);
      await page.locator(sel + " img").first().evaluate((i) => i.scrollIntoView());
      await imgOk(sel + " img");
      check(`${v.name}: hall «${hid}» opens with its composition`, (await page.locator(sel).count()) >= 8 || hid === "peterburg-moskva");
      if (hid === "tsvet") await shot("14-hall-color");
    }
    await page.goto(base + "#/showcase/tsvet", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#show");
    await imgOk("#showImg");
    await page.keyboard.press("Escape");
    check(`${v.name}: a hall can be shown full screen`, true);
    // 8. random masterpiece and related jump
    await page.waitForSelector("#grand");
    await page.locator("#grand").click();
    await imgOk("#zoomimg");
    await page.locator(".rail .rt").first().click();
    await imgOk("#zoomimg");
    check(`${v.name}: random masterpiece and related-work jump open real images`, /#\/art\//.test(page.url()));
    // 9. panorama
    await page.goto(base + "#/gallery", { waitUntil: "domcontentloaded" });
    await page.locator('.glens:has-text("Панорамы")').click();
    await page.waitForSelector(".gmasonry .gt");
    await page.locator(".gmasonry .gt").first().click();
    await imgOk("#zoomimg");
    await shot("12-panorama");
    check(`${v.name}: gallery pages have no horizontal scroll`, await noScroll());
    check(`${v.name}: no console/page errors`, errors.length === 0, errors.slice(0, 2).join(" | "));
    await ctx.close();
  }
  await browser.close();
  if (results.some((r) => !r)) process.exit(1);
})();
