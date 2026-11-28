// Angle search on a sheet page with the network mocked: ranking, honest labels, curtain, own photo stays local.
// Usage: NODE_PATH=$(npm root -g) node tests/browser/qa_angles.js http://127.0.0.1:8765/book/
const { chromium } = require("playwright");
const base = process.argv[2];
if (!base) throw Error("Usage: qa_angles.js <url of book/>");
const results = [];
const check = (name, ok, detail = "") => { results.push(ok); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail}`); };
const PX = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==", "base64");
(async () => {
  const browser = await chromium.launch();
  for (const v of [{ name: "iphone-390", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }, { name: "desktop-1280", viewport: { width: 1280, height: 900 } }]) {
    const ctx = await browser.newContext(v), page = await ctx.newPage(), errs = [], uploads = [];
    page.on("pageerror", (e) => errs.push(String(e)));
    page.on("request", (r) => { if (r.method() === "POST") uploads.push(r.url()); });
    await page.route(/tile\.openstreetmap/, (r) => r.abort());
    // sheet parismusees-320291945 = Notre-Dame, approx 48.85294, 2.35005
    const feat = (id, dlat, dlon, az, who) => ({ id, geometry: { type: "Point", coordinates: [2.35005 + dlon, 48.85294 + dlat] }, collection: "c1", properties: { datetimetz: "2025-06-01T10:00:00Z", "view:azimuth": az, "geovisio:producer": who, license: "CC-BY-SA-4.0" }, assets: { thumb: { href: "https://px.test/t.png" }, sd: { href: "https://px.test/s.png" } } });
    await page.route(/panoramax\.ign\.fr\/api\/search/, (r) => r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify({ features: [feat("far-looking-away", 0.0006, 0, 0, "A"), feat("near-facing", 0.0004, 0, 180, "B")] }) }));
    await page.route(/api\.panoramax\.xyz\/api\/search/, (r) => r.abort());
    await page.route(/commons\.wikimedia\.org\/w\/api\.php/, (r) => r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(/geosearch/.test(r.request().url()) ? { query: { geosearch: [{ pageid: 7, title: "File:Test.jpg", lat: 48.8531, lon: 2.3502 }] } } : { query: { pages: { 7: { title: "File:Test.jpg", imageinfo: [{ thumburl: "https://px.test/c.png", url: "https://px.test/c.png", descriptionurl: "https://commons.wikimedia.org/wiki/File:Test.jpg", extmetadata: { Artist: { value: "<b>Tester</b>" }, LicenseShortName: { value: "CC BY-SA 4.0" }, DateTimeOriginal: { value: "2024-05-05" } } }] } } } }) }));
    await page.route("https://px.test/**", (r) => r.fulfill({ status: 200, contentType: "image/png", body: PX }));
    await page.goto(base + "#/sheet/parismusees-320291945", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#angGo");
    check(`${v.name}: angle search offers radius, search and own photo, and says coordinates are approximate`, (await page.locator("#angR").count()) === 1 && (await page.locator(".angup").count()) === 1 && /приблизительные/.test(await page.locator(".anglesearch").innerText()));
    await page.locator("#angGo").click();
    await page.waitForSelector(".angc");
    const order = await page.evaluate(() => window.__angles.map((c) => c.id));
    const labels = await page.locator(".angc span").allInnerTexts();
    check(`${v.name}: candidates are ranked: near and facing first, far and looking away later`, order.indexOf("near-facing") < order.indexOf("far-looking-away"), order.join(","));
    check(`${v.name}: labels state distance, camera direction, author and licence`, /смотрит на здание/.test(labels.join()) && /смотрит в сторону/.test(labels.join()) && /CC BY-SA 4\.0/.test(labels.join()) && /Wikimedia/.test(labels.join()));
    check(`${v.name}: a source that does not answer is named, not hidden`, /Не ответили: Panoramax \(федерация\)/.test(await page.locator("#angNote").innerText()));
    await page.locator(".angc").first().click();
    await page.waitForSelector("#angCurtain");
    await page.locator("#angRange").fill("20");
    check(`${v.name}: selected candidate opens as a curtain of two independent pictures with a stated non-alignment`, (await page.locator("#angCurtain .cB").evaluate((e) => e.style.clipPath)).includes("20%") && /не совпадают/.test(await page.locator("#angCmp").innerText()));
    const m = await page.evaluate(() => { const M = window.CoPBook.angleMath; return [Math.round(M.dist({ lat: 48.85, lon: 2.35 }, { lat: 48.86, lon: 2.35 })), Math.round(M.bearing({ lat: 48.85, lon: 2.35 }, { lat: 48.86, lon: 2.35 })), M.angDiff(350, 10)]; });
    check(`${v.name}: distance, bearing and angular difference are correct`, Math.abs(m[0] - 1112) < 5 && m[1] === 0 && m[2] === 20, m.join(","));
    await page.locator("#angFile").setInputFiles({ name: "mine.png", mimeType: "image/png", buffer: PX });
    await page.waitForFunction(() => /Ваше фото/.test(document.getElementById("angCmp").innerText));
    check(`${v.name}: own photo is shown locally and nothing is uploaded`, uploads.length === 0);
    check(`${v.name}: no horizontal scroll and no page errors`, (await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 4)) && errs.length === 0, errs.join("|"));
    await ctx.close();
  }
  await browser.close();
  if (results.some((r) => !r)) process.exit(1);
})();
