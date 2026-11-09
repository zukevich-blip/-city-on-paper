// Issue #34 "Atlas of eras" prototype QA. Usage: node tests/browser/qa_eras.js http://127.0.0.1:8791/ <outdir>
const { chromium } = require("playwright");
const [, , base, out] = process.argv;
const res = [];
const ok = (n, c, d = "") => { res.push({ n, c, d }); console.log(`${c ? "PASS" : "FAIL"} ${n} ${d}`); };
(async () => {
  const b = await chromium.launch();
  for (const vp of [{ n: "phone-390", w: 390, h: 844, m: true }, { n: "tablet-820", w: 820, h: 1180, m: true }, { n: "desktop-1440", w: 1440, h: 900 }]) {
    const ctx = await b.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: !!vp.m, hasTouch: !!vp.m, reducedMotion: vp.n === "phone-390" ? "reduce" : "no-preference" });
    const p = await ctx.newPage(); const errs = [];
    // Curation files generated at packaging time (absent in a source checkout, present in the built site).
    const GENERATED = /data\/curation\/(world-graphic-archive-v1|museum-expansion-v1)\.json$/;
    p.on("pageerror", e => errs.push(String(e)));
    p.on("console", m => m.type() === "error" && !/Failed to load resource/.test(m.text()) && errs.push(m.text()));
    p.on("response", r => { if (r.status() >= 400 && !GENERATED.test(r.url())) errs.push(`${r.status()} ${r.url()}`); });
    await p.goto(base + "eras/", { waitUntil: "networkidle" });
    const nCities = await p.$$eval(".ccard", (c) => c.length);
    ok(`${vp.n} portal: city list ≥ 80`, nCities >= 80, String(nCities));
    ok(`${vp.n} geographic country index`,
      (await p.locator("#countryIndex .country-chip").count()) >= 20 &&
      (await p.locator("#list .country-group").count()) >= 20);
    await p.locator("#countriesClose").click();
    ok(`${vp.n} country chapters close`,
      (await p.locator("#list .country-group[open]").count()) === 0);
    await p.locator("#countriesOpen").click();
    ok(`${vp.n} country chapters open`,
      (await p.locator("#list .country-group[open]").count()) >= 20);

    await p.goto(base + "eras/#/country/" + encodeURIComponent("Италия"), { waitUntil: "networkidle" });
    ok(`${vp.n} shareable country chapter`,
      (await p.locator("#grp").inputValue()) === "r:Италия" &&
      (await p.locator(".country-group").count()) === 1);
    await p.goto(base + "eras/#/", { waitUntil: "networkidle" });
    await p.waitForTimeout(600);
    await p.waitForFunction(() => document.querySelectorAll("#pmap .leaflet-tile-loaded").length >= 1,
      null, { timeout: 10000 });
    const mapTileCount = await p.locator("#pmap .leaflet-tile-loaded").count();
    const mapTileUrl = await p.locator("#pmap .leaflet-tile").first().evaluate(img => img.src);
    const mapTileResponse = await p.request.get(mapTileUrl);
    ok(`${vp.n} portal: historical map tile loaded and served`,
      mapTileCount >= 1 && mapTileResponse.ok() && String(mapTileResponse.headers()["content-type"] || "").startsWith("image/"),
      `${mapTileCount} / ${mapTileResponse.status()} / ${mapTileUrl}`);
    ok(`${vp.n} portal: pins on map`, (await p.locator("#pmap .mk").count()) >= 150);
    ok(`${vp.n} museum bar: all halls`, await p.$eval("#museumPanel a", (a) => a.length) >= 18);
    ok(`${vp.n} closed halls never cover the museum at rest`,
      await p.locator("#museumPanel").evaluate(el =>
        el.hidden && getComputedStyle(el).display === "none"));
    await p.locator("#museumBar button").click();
    ok(`${vp.n} full museum navigation opens on demand`,
      await p.locator("#museumPanel").isVisible() &&
      (await p.locator("#museumBar button").getAttribute("aria-expanded")) === "true");
    await p.keyboard.press("Escape");
    ok(`${vp.n} Escape dismisses menu and restores trigger focus`,
      await p.locator("#museumPanel").evaluate(el =>
        el.hidden && getComputedStyle(el).display === "none" &&
        document.activeElement === document.querySelector("#museumBar button")));
    ok(`${vp.n} portal has a complete clickable exploration route`,
      (await p.locator(".museum-journey .museum-journey-step").count()) === 4);
    await p.fill("#q", "Лиссаб");
    ok(`${vp.n} portal: search filters list`, (await p.$$eval(".ccard", (c) => c.map((x) => x.textContent))).every((t) => /Лиссабон/.test(t)) && (await p.locator(".ccard").count()) >= 1);
    await p.fill("#q", "");
    await p.selectOption("#grp", "featured");
    ok(`${vp.n} portal: featured filter`, (await p.locator(".ccard").count()) === 3);
    ok(`${vp.n} portal: filter announced`, /Показано 3 город/.test(await p.textContent("#shown")));
    await p.selectOption("#grp", "all");
    const zoomOf = () => p.$eval("#pmap .leaflet-map-pane", (m) => m.querySelector(".leaflet-tile-container") ? 1 : 0)
      .then(() => p.evaluate(() => document.querySelector("#pmap .leaflet-proxy").style.transform));
    const z0 = await zoomOf();
    await p.click("#pmap .leaflet-control-zoom-in"); await p.waitForTimeout(700);
    ok(`${vp.n} portal: zoom button in the corner works`, (await zoomOf()) !== z0);
    const zb = await p.$eval("#pmap .leaflet-control-zoom-in", (b) => { const r = b.getBoundingClientRect(), m = b.closest(".lmap").getBoundingClientRect(); return [r.width, m.right - r.right, r.top - m.top]; });
    ok(`${vp.n} portal: zoom control is ≥44px, top-right`, zb[0] >= 44 && zb[1] < 30 && zb[2] < 30, zb.join(","));
    await p.click("#pmap .mhome"); await p.waitForTimeout(500);
    await p.click("#tNew"); await p.waitForTimeout(800);
    ok(`${vp.n} portal: modern map tab`, (await p.locator("#nmap .mk").count()) >= 180);
    await p.click("#tOld");
    await p.screenshot({ path: `${out}/${vp.n}-1-portal.jpg`, type: "jpeg", quality: 60 });
    const man = await p.evaluate(async () => { const l = document.querySelector('link[rel="manifest"]'); const r = await fetch(l.href); const j = await r.json(); return j.display + "|" + j.icons.length; });
    ok(`${vp.n} PWA manifest`, man === "standalone|3", man);
    const sw = await p.evaluate(() => Promise.race([navigator.serviceWorker.ready.then(() => true), new Promise((r) => setTimeout(() => r(false), 6000))]));
    ok(`${vp.n} service worker registered`, sw);
    await p.click("#fbBtn");
    ok(`${vp.n} feedback dialog opens`, await p.$eval("#fb", (d) => d.open));
    await p.click('#fb input[name="r"][value="5"]');
    await p.fill("#fbText", "Тестовый отзыв");
    await p.click("#fbSend");
    await p.waitForTimeout(300);
    ok(`${vp.n} feedback gives a status`, (await p.textContent("#fbStatus")).length > 5, await p.textContent("#fbStatus"));
    await p.click('#fb button[value="cancel"]');
    const lisbonChapter = p.locator(".country-group", { hasText: "Лиссабон" });
    if (!(await lisbonChapter.evaluate(el => el.open))) await lisbonChapter.locator("summary").click();
    await p.locator(".ccard", { hasText: "Лиссабон" }).click();
    await p.waitForSelector("#wg");
    ok(`${vp.n} generic city page`, /Лиссабон/.test(await p.textContent("h1")) && (await p.locator(".hunt2 a").count()) === 4);
    ok(`${vp.n} every city gives a full museum research chain`,
      (await p.locator('nav.museum-journey[aria-label="Маршрут исследования города"] .museum-journey-step').count()) === 5 &&
      (await p.locator("#archiveSearch").count()) === 1);
    const cityHash = await p.evaluate(() => location.hash);
    await p.locator(".museum-journey .museum-journey-step").first().click();
    ok(`${vp.n} city map trail scrolls without destroying hash route`,
      (await p.evaluate(() => location.hash)) === cityHash);
    await p.locator("#historicCartography .historic-map-search a").waitFor();
    ok(`${vp.n} any city gets a source-backed historical map search`,
      (await p.locator("#historicCartography .historic-map-search a").getAttribute("href")).startsWith("https://www.loc.gov/maps/?q="));
    await p.locator("#cityLab [data-role='search']").waitFor();
    ok(`${vp.n} city study lab available in a generic city`,
      await p.locator("#cityLab [data-role='search']").isVisible() &&
      await p.locator("#cityLab [data-role='selected']").isVisible());

    await p.goto(base + "eras/#/", { waitUntil: "networkidle" });
    const parisChapter = p.locator(".country-group", { hasText: "Париж" });
    if (!(await parisChapter.evaluate(el => el.open))) await parisChapter.locator("summary").click();
    await p.locator(".ccard", { hasText: "Париж" }).first().click();
    await p.waitForSelector(".places a");
    ok(`${vp.n} city: plan with place pins`, (await p.locator(".plate .pin").count()) === 2);
    await p.locator("#historicCartography .historic-map-source a").waitFor();
    ok(`${vp.n} Paris has an authentic historic map source citation`,
      (await p.locator("#historicCartography .historic-map-source a").getAttribute("href")) ===
      "https://www.loc.gov/item/2012586603/" &&
      /геопривязка ещё не проверена/.test(await p.locator("#historicCartography").textContent()));
    ok(`${vp.n} featured city also lists museum works`, (await p.locator("#others").count()) === 1);
    await p.waitForFunction(() => /всего \d+ доступных изображений/.test(
      document.querySelector('#cityLab [data-role="status"]')?.textContent || ""));
    ok(`${vp.n} all-artist city lab renders visual records`,
      (await p.locator("#cityLab .citylab-item").count()) >= 2);
    ok(`${vp.n} city lab can compare selected different museum works`,
      await p.locator("#cityLab .chronoscope").isVisible());
    await p.locator("#cityLab .citylab-item button").first().click();
    ok(`${vp.n} any print can open an enlarged source dossier`,
      await p.locator("#cityLab [data-role='viewer']").evaluate(x => x.open) &&
      (await p.locator("#cityLab [data-role='viewer-facts'] a").count()) >= 1);
    await p.locator("#cityLab [data-role='zoom-in']").click();
    ok(`${vp.n} city print zoom`,
      await p.locator("#cityLab [data-role='viewer'] [data-role='zoom-value']").textContent() === "150%" &&
      (await p.locator("#cityLab [data-role='viewer-image']").evaluate(el => el.style.transform)).includes("scale(1.5)"));
    await p.locator("#cityLab [data-role='close']").click();
    const localPhoto = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9eLp3WEAAAAASUVORK5CYII=", "base64");
    const selectedBeforePhoto = await p.locator("#cityLab [data-role='selected']").textContent();
    await p.locator("#cityLab [data-role='user-photo']").setInputFiles({
      name: "new-city-view.png", mimeType: "image/png", buffer: localPhoto
    });
    ok(`${vp.n} city lab accepts local rephotography`,
      /Фото добавлено локально/.test(await p.locator("#cityLab [data-role='photo-status']").textContent()) &&
      (await p.locator("#cityLab [data-role='selected']").textContent()) !== selectedBeforePhoto);
    ok(`${vp.n} locally added image can join historical comparison`,
      (await p.locator("#cityLab .chronoscope [data-role='count']").textContent()).includes("4 из 4"));
    await p.locator("#cityLab [data-role='remove-photo']").click();
    ok(`${vp.n} city lab removes local photo`,
      (await p.locator("#cityLab [data-role='selected']").textContent()) === selectedBeforePhoto);

    const beforeSelection = (await p.locator("#cityLab [data-role='selected']").textContent());
    await p.locator("#cityLab .citylab-item input[type='checkbox']").first().uncheck();
    const afterSelection = (await p.locator("#cityLab [data-role='selected']").textContent());
    ok(`${vp.n} user-selected work alters city timeline`, beforeSelection !== afterSelection);
    await p.locator("#cityLab .citylab-item input[type='checkbox']").first().check();
    await p.locator("#cityLab [data-role='search']").fill("___no_city_2026_print___");
    ok(`${vp.n} city studio artwork search`,
      (await p.locator("#cityLab .citylab-item").count()) === 0);
    await p.locator("#cityLab [data-role='search']").fill("");

    ok(`${vp.n} city offers author and artwork search`,
      await p.locator("#museumAuthor").isVisible() && await p.locator("#museumQuery").isVisible());
    await p.waitForFunction(() => /Найдено/.test(document.querySelector("#museumCount")?.textContent || ""));
    const initialWorks = await p.locator("#wg .wcard").count();
    await p.locator("#museumAuthor").fill("___no_such_lithographer_2026___");
    ok(`${vp.n} author filter excludes unrelated prints`,
      (await p.locator("#wg .wcard").count()) === 0 && /Найдено 0/.test(await p.locator("#museumCount").textContent()));
    await p.locator("#museumAuthor").fill("");
    ok(`${vp.n} author filter restores all works`,
      (await p.locator("#wg .wcard").count()) === initialWorks);

    await p.locator("#cmaphost").scrollIntoViewIfNeeded(); await p.waitForTimeout(800);
    ok(`${vp.n} city: zoomable 1878 plan of Paris`, (await p.locator("#cplan .leaflet-tile-loaded").count()) >= 2);
    ok(`${vp.n} city: links to other museum halls`, (await p.locator(".halls a").count()) >= 3);
    await p.screenshot({ path: `${out}/${vp.n}-2-paris.jpg`, type: "jpeg", quality: 60 });
    await p.locator(".plate .pin", { hasText: "Мадлен" }).click();
    await p.waitForSelector("#stage");
    await p.waitForFunction(() => document.getElementById("imA").complete && document.getElementById("imB").complete);
    ok(`${vp.n} place: timeline cards`, (await p.locator(".era-card").count()) >= 8);
    ok(`${vp.n} triple time slider available`, await p.locator("#threeEpochs").isVisible());
    ok(`${vp.n} triple timeline has 3 actual images`, await p.locator("#threeEpochs .cp3-stage img").count() === 3);
    ok(`${vp.n} triple timeline all source links`, (await p.locator("#threeEpochs .cp3-sources a").count()) === 3);
    await p.locator('#threeEpochs [data-go="0"]').click();
    ok(`${vp.n} triple stage: 0% shows first era`, await p.locator('#threeEpochs [data-role="position"]').inputValue() === "0");
    await p.locator('#threeEpochs [data-go="50"]').click();
    ok(`${vp.n} triple stage: 50% shows middle era`, await p.locator('#threeEpochs [data-role="position"]').inputValue() === "50");
    await p.locator('#threeEpochs [data-go="100"]').click();
    ok(`${vp.n} triple stage: 100% shows last era`, await p.locator('#threeEpochs [data-role="position"]').inputValue() === "100");
    ok(`${vp.n} triple stage: third image fully revealed`, await p.locator('#threeEpochs [data-role="layer-last"]').evaluate(x => { const m = /inset\(0(?:px)? ([\d.]+)%/.exec(x.style.clipPath); return Boolean(m) && Number(m[1]) === 0; }));
    const baselineFrames = await p.locator('#threeEpochs [data-role="last"] option').count();
    const localFixture = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9eLp3WEAAAAASUVORK5CYII=", "base64");
    await p.locator('#threeEpochs [data-role="upload-photo"]').setInputFiles({ name: "my-photo.png", mimeType: "image/png", buffer: localFixture });
    ok(`${vp.n} local photo: third epoch selected`, await p.locator('#threeEpochs [data-role="last"]').inputValue() === String(baselineFrames));
    ok(`${vp.n} local photo: no server upload in UI`, /только в этот просмотр/.test(await p.locator('#threeEpochs [data-role="photo-status"]').textContent()));
    await p.locator('#threeEpochs [data-role="remove-photo"]').click();
    ok(`${vp.n} local photo: removed`, (await p.locator('#threeEpochs [data-role="last"] option').count()) === baselineFrames);
    await p.screenshot({ path: `${out}/${vp.n}-4-three-epochs.jpg`, type: "jpeg", quality: 60 });
    ok(`${vp.n} chronoscope available`, await p.locator("#chronoscope").isVisible());
    const allFrames = await p.locator('#chronoscope .cs-choices input').count();
    const availableOriginals = await p.locator(".era-card img").count();
    ok(`${vp.n} chronoscope displays all available archival frames`, allFrames === availableOriginals && allFrames >= 3, `${allFrames}/${availableOriginals}`);
    ok(`${vp.n} chronoscope one-keyframe-per-frame`,
      (await p.locator('#chronoscope .cs-keyframes button').count()) === allFrames);
    ok(`${vp.n} chronoscope whole range`,
      +(await p.locator('#chronoscope [data-role="range"]').getAttribute("max")) === (allFrames - 1) * 100);
    await p.locator('#chronoscope .cs-choices input').first().uncheck();
    ok(`${vp.n} chronoscope excludes chosen frame`,
      (await p.locator('#chronoscope .cs-keyframes button').count()) === allFrames - 1);
    await p.locator('#chronoscope .cs-choices input').first().check();
    ok(`${vp.n} chronoscope restores archival frame`,
      (await p.locator('#chronoscope .cs-keyframes button').count()) === allFrames);
    await p.locator('#chronoscope [data-zoom="in"]').click();
    const zoomed = await p.locator('#chronoscope [data-role="a"]').evaluate(el => el.style.transform);
    ok(`${vp.n} chronoscope zoom magnifies detail`, zoomed.includes("scale(1.5)"), zoomed);
    const matched = await p.locator('#chronoscope .cs-stage').evaluate(stage =>
      stage.querySelector('[data-role="a"]').style.transform === stage.querySelector('[data-role="b"]').style.transform);
    ok(`${vp.n} chronoscope zoom matches both epochs`, matched);
    await p.locator('#chronoscope [data-zoom="reset"]').click();
    ok(`${vp.n} chronoscope zoom resets`,
      (await p.locator('#chronoscope [data-role="zoom-value"]').textContent()) === "100%");
    await p.locator('#chronoscope .cs-keyframes button').last().click();
    ok(`${vp.n} chronoscope last epoch selected`,
      +(await p.locator('#chronoscope [data-role="range"]').inputValue()) === (allFrames - 1) * 100);
    ok(`${vp.n} chronoscope source attribution`,
      (await p.locator('#chronoscope .cs-provenance a').count()) >= 2);
    await p.screenshot({ path: `${out}/${vp.n}-5-all-eras-zoom.jpg`, type: "jpeg", quality: 60 });
    ok(`${vp.n} Madeleine architectural desk present`,
      await p.locator("#curatorialDesk").isVisible() && /Мадлен/.test(await p.locator("#curatorialDesk h2").textContent()));
    ok(`${vp.n} architectural glossary explains at least three details`,
      (await p.locator("#curatorialDesk .cd-section").first().locator(".cd-item").count()) >= 3);
    ok(`${vp.n} architecture and printmaking sources linked`,
      (await p.locator("#curatorialDesk .cd-item a[href^='https://']").count()) >= 10);
    ok(`${vp.n} historical fact distinguishes 1842 and 1845-1860`,
      /1842/.test(await p.locator("#curatorialDesk").textContent()) &&
      /1845/.test(await p.locator("#curatorialDesk").textContent()));
    ok(`${vp.n} place: verdict shown`, /совпадение|точки съёмки|ракурс/i.test(await p.textContent("#verdict")));
    ok(`${vp.n} place: camera cones on 1878 plan`, (await p.locator(".cam").count()) >= 5);
    const untouched = await p.$$eval(".era-card img, .plate img", ims => ims.every(i => { const s = getComputedStyle(i); return s.transform === "none" && s.filter === "none"; }));
    ok(`${vp.n} historic images: no transform/filter`, untouched);
    const broken = await p.$$eval("img", ims => ims.filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute("src")).map(i => i.src));
    ok(`${vp.n} no broken images`, broken.length === 0, broken.join(","));
    await p.focus("#handle"); await p.keyboard.press("Home");
    ok(`${vp.n} slider keyboard Home`, (await p.getAttribute("#handle", "aria-valuenow")) === "0");
    await p.keyboard.press("ArrowRight");
    ok(`${vp.n} slider keyboard step`, (await p.getAttribute("#handle", "aria-valuenow")) === "2");
    const box = await p.locator("#stage").boundingBox();
    await p.mouse.click(box.x + box.width * 0.25, box.y + box.height / 2);
    ok(`${vp.n} slider pointer`, Math.abs(+(await p.getAttribute("#handle", "aria-valuenow")) - 25) <= 2);
    await p.locator(".camlist button:not([disabled])").nth(1).click();
    ok(`${vp.n} camera list selects image`, (await p.$eval("#selA", s => s.options[s.selectedIndex].text)).includes("1860"));
    ok(`${vp.n} opacity disabled for non-close pair`, await p.$eval('[data-m="opacity"]', b => b.disabled));
    await p.selectOption("#selA", { label: "ок. 1890–1900 · Фотохром" }).catch(() => {});
    const opts = await p.$$eval("#selB option", os => os.map(o => o.textContent));
    const der = await p.$$eval("#selB option", os => os.findIndex(o => /2017/.test(o.textContent)));
    if (der >= 0) { await p.selectOption("#selB", { index: der }); ok(`${vp.n} derived crop labelled in compare`, /производная/.test(await p.textContent("#tagB")), opts.join("/")); }
    await p.click('[data-m="sbs"]');
    ok(`${vp.n} side-by-side exclusive`, await p.evaluate(() => document.getElementById("stage").hidden && !document.getElementById("sbs").hidden));
    await p.click('[data-m="slider"]');
    await p.locator("#stage").scrollIntoViewIfNeeded();
    await p.screenshot({ path: `${out}/${vp.n}-3-madeleine.jpg`, type: "jpeg", quality: 60, fullPage: vp.n === "phone-390" });
    const small = await p.$$eval("button, select, a.pin, a.ccard", els => els.filter(e => e.offsetParent).map(e => e.getBoundingClientRect()).filter(r => r.height < 40 || r.width < 36).length);
    ok(`${vp.n} touch targets ≥40px`, small === 0, `${small} small`);
    ok(`${vp.n} no horizontal page scroll`, await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    ok(`${vp.n} images have alt`, await p.$$eval("img:not(.leaflet-tile)", ims => ims.every(i => (i.alt || "").length > 5)));
    await p.goto(base + "eras/#/epochs", { waitUntil: "networkidle" });
    ok(`${vp.n} epochs gallery`, (await p.locator(".epcard").count()) >= 50);
    await p.locator(".epcard").first().click(); await p.waitForSelector("#epstage"); await p.waitForTimeout(600);
    ok(`${vp.n} epoch place: frames + angle map`, (await p.locator(".epf[data-f]").count()) >= 2 && (await p.locator("#epMap .leaflet-tile").count()) >= 1);
    await p.click("#epAdd");
    ok(`${vp.n} my photo dialog (local only)`, await p.$eval("#epDlg", (d) => d.open && /только на этом устройстве/.test(d.textContent)));
    await p.click('#epDlg button[value="cancel"]');
    await p.goto(base + "eras/#/mine", { waitUntil: "networkidle" });
    await p.waitForFunction(() => /Мой ракурс/.test((document.querySelector("h1") || {}).textContent || ""), null, { timeout: 5000 }).catch(() => {});
    ok(`${vp.n} my viewpoints page`, /Мой ракурс/.test(await p.textContent("h1")));
    await p.goto(base + "eras/#/place/naples-santa_lucia_castel_dell_ovo", { waitUntil: "networkidle" });
    ok(`${vp.n} Naples place renders honest mismatch`, /Разные точки/.test(await p.textContent("#verdict")));
    ok(`${vp.n} uncatalogued place gets source-led research checklist`, /Как исследовать старую литографию/.test(await p.locator("#curatorialDesk h2").textContent()));
    await p.goto(base + "eras/#/place/nope", { waitUntil: "networkidle" });
    ok(`${vp.n} unknown route handled`, /Не найдено/.test(await p.textContent("#app")));
    await p.goto(base + "desk/", { waitUntil: "networkidle" });
    await p.waitForSelector("#albumStack .album-book");
    ok(`${vp.n} design prototype uses real map and city albums`,
      (await p.locator("#albumStack .album-book").count()) >= 5 &&
      await p.locator("#pmap").isVisible() &&
      await p.locator("#tNew").isVisible());
    await p.locator("#albumStack .album-book[data-city='paris']").click();
    ok(`${vp.n} city album opens with real source references`,
      await p.locator("#folioDialog").evaluate(d=>d.open) &&
      /Париж/.test(await p.locator("#folioSpread").textContent()));
    await p.locator("#folioNext").click();
    ok(`${vp.n} city folio flips`,
      (await p.locator("#folioPage").textContent()) === "2 / 3");
    await p.locator("#folioClose").click();
    await p.locator(".mode-toggle [data-mode='book']").click();
    ok(`${vp.n} map and book view switch is functional`,
      (await p.locator("body").getAttribute("data-mode")) === "book");
    await p.locator("#citySearch").fill("Венеция");
    ok(`${vp.n} desk city finder navigates to true catalog city`,
      (await p.locator("#suggestions a[href*='/city/venetsiya']").count()) >= 1);
    await p.screenshot({ path: `${out}/${vp.n}-7-antique-desk-design.jpg`, type: "jpeg", quality: 67 });
    const designHasOverflow = await p.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 3);
    ok(`${vp.n} desk prototype no horizontal overflow`, !designHasOverflow);

    ok(`${vp.n} no console/page/HTTP errors`, errs.length === 0, errs.slice(0, 3).join(" | "));
    // The main entrance and world atlas use different local layouts but share
    // the same museum top bar. Test actual computed CSS, not just HTML hidden.
    const museum = await ctx.newPage();
    for (const route of ["", "world/"]) {
      await museum.goto(base + route, { waitUntil: "domcontentloaded" });
      await museum.locator("#museumPanel").waitFor({ state: "attached" });
      const section = route || "home";
      ok(`${vp.n} ${section} menu starts physically collapsed`,
        await museum.locator("#museumPanel").evaluate(el =>
          el.hidden && getComputedStyle(el).display === "none"));
      ok(`${vp.n} ${section} no horizontal page overflow`,
        await museum.evaluate(() => document.documentElement.scrollWidth <=
          document.documentElement.clientWidth + 5));
      await museum.screenshot({
        path: `${out}/${vp.n}-museum-${section}-polished.jpg`,
        type: "jpeg", quality: 72,
      });
    }
    const noSourceDistortion = await museum.evaluate(() => {
      const fig = document.createElement("figure");
      const img = document.createElement("img");
      const box = document.createElement("div"); box.className = "city";
      fig.appendChild(img); box.appendChild(fig); document.body.appendChild(box);
      const computed = getComputedStyle(img);
      const ok = computed.objectFit === "contain" && computed.filter === "none";
      box.remove();
      return ok;
    });
    ok(`${vp.n} world museum art shown without crop or CSS desaturation`,
      noSourceDistortion);
    await museum.close();
    await ctx.close();
  }
  await b.close();
  const f = res.filter(r => !r.c).length;
  require("fs").writeFileSync(`${out}/qa-eras-results.json`, JSON.stringify({ when: new Date().toISOString(), passed: res.length - f, failed: f, results: res }, null, 1));
  console.log(`\n${res.length - f} passed, ${f} failed`); process.exit(f ? 1 : 0);
})();
