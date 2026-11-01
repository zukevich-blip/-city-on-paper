// Browser QA for poc/compare (viewer + control-point editor).
// Usage: NODE_PATH=$(npm root -g) node tests/browser/qa_compare.js http://127.0.0.1:8766/poc/compare/ docs/screens
const { chromium } = require("playwright");
const fs = require("fs");
const [, , base, outDir] = process.argv;
const viewports = [
  { name: "iphone-375", width: 375, height: 812, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
  { name: "iphone-390", width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
  { name: "ipad-820", width: 820, height: 1180, isMobile: true, hasTouch: true, deviceScaleFactor: 1 },
  { name: "desktop-1440", width: 1440, height: 900, deviceScaleFactor: 1 },
];
const PAIRS = ["madeleine-ph-benoist", "palais-royal-ph-benoist", "synthetic-near-identical", "synthetic-rotation-only", "synthetic-parallax"];
const origin = new URL(base).origin;
const results = [];
const check = (name, ok, detail = "") => { results.push({ name, ok: !!ok, detail }); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail}`); };
const shot = (page, file, opts = {}) => page.screenshot({ path: `${outDir}/${file}`, type: "jpeg", quality: 65, scale: "css", ...opts });

function watch(page) {
  const errors = [], offsite = [];
  page.on("pageerror", e => errors.push(String(e)));
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("request", r => { const u = r.url(); if (!u.startsWith(origin) && !u.startsWith("blob:") && !u.startsWith("data:")) offsite.push(u); });
  return { errors, offsite };
}

async function viewerChecks(browser, vp) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile,
    hasTouch: !!vp.hasTouch, deviceScaleFactor: vp.deviceScaleFactor, reducedMotion: vp.name === "iphone-375" ? "reduce" : "no-preference" });
  const page = await ctx.newPage();
  const w = watch(page);
  for (const id of PAIRS) {
    await page.goto(`${base}?split=55#${id}`, { waitUntil: "networkidle" });
    await page.waitForFunction((id) => document.getElementById("pairSel").value === id &&
      document.getElementById("histImg").complete && document.getElementById("photoLayer").style.transform !== "" &&
      document.getElementById("credits").textContent.length > 50, id);
    await page.waitForTimeout(150);
    const pair = await page.evaluate(async (id) => (await (await fetch(`pairs/${id}.json`)).json()), id);
    const conf = pair.alignment.confidence;
    if (conf === "viewpoint_mismatch") {
      const st = await page.evaluate(() => ({
        sbs: getComputedStyle(document.getElementById("sbs")).display !== "none",
        stage: getComputedStyle(document.getElementById("stage")).display !== "none",
        alignDisabled: document.getElementById("alignBtn").disabled }));
      check(`${vp.name} ${id}: viewpoint_mismatch opens side by side, alignment button disabled`, st.sbs && !st.stage && st.alignDisabled);
      check(`${vp.name} ${id}: viewpoint_mismatch never applies matrix3d`, (await page.$eval("#photoLayer", e => e.style.transform)).startsWith("translate"));
      if (id === "palais-royal-ph-benoist") await shot(page, `${vp.name}-${id}-side-by-side.jpg`, { fullPage: vp.name !== "iphone-375" });
    } else {
      if (!["high", "medium"].includes(conf)) {
        check(`${vp.name} ${id}: '${conf}' opens with the untouched photo`,
          (await page.$eval("#photoLayer", e => e.style.transform)).startsWith("translate"));
        await page.click("#alignBtn");
      }
      // math check: CSS transform of the photo layer must send each photo control point onto its historic point
      const err = await page.evaluate((pair) => {
        const L = document.getElementById("photoLayer"), st = document.getElementById("stage");
        const m = new DOMMatrix(getComputedStyle(L).transform);
        const s = st.clientWidth / pair.historic.size[0];
        let worst = 0;
        pair.control_points.forEach((c, i) => {
          const p = m.transformPoint(new DOMPoint(c.photo[0], c.photo[1], 0, 1));
          const r = Math.hypot(p.x / p.w / s - c.historic[0], p.y / p.w / s - c.historic[1]);
          worst = Math.max(worst, Math.abs(r - pair.alignment.residuals_px[i]));
        });
        return worst;
      }, pair);
      check(`${vp.name} ${id}: CSS matrix3d reproduces offline residuals`, err < 0.1, `max |Δ| = ${err.toFixed(4)} px`);
      const exclusive = await page.evaluate(() => {
        const vis = (id) => getComputedStyle(document.getElementById(id)).display !== "none";
        return vis("stage") && !vis("sbs");
      });
      check(`${vp.name} ${id}: slider mode hides side-by-side panel`, exclusive);
    }
    const histUntouched = await page.evaluate(() => [document.getElementById("histImg"), document.getElementById("sbsHist")].every(h => {
      const cs = getComputedStyle(h); return cs.transform === "none" && cs.filter === "none" && h.naturalWidth > 0; }));
    check(`${vp.name} ${id}: historic image has no transform/filter`, histUntouched);
    check(`${vp.name} ${id}: no horizontal page scroll`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    if (id === "madeleine-ph-benoist" || vp.name === "desktop-1440")
      await shot(page, `${vp.name}-${id}-slider.jpg`, { fullPage: vp.name === "iphone-390" || vp.name === "ipad-820" });
  }
  // interactions on the real Madeleine pair (verdict low: local fit, opens unaligned)
  await page.goto(`${base}#madeleine-ph-benoist`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.getElementById("photoLayer").style.transform !== "");
  await page.focus("#handle"); await page.keyboard.press("Home");
  check(`${vp.name}: keyboard Home moves slider to 0`, (await page.getAttribute("#handle", "aria-valuenow")) === "0");
  await page.keyboard.press("ArrowRight");
  check(`${vp.name}: ArrowRight steps slider`, (await page.getAttribute("#handle", "aria-valuenow")) === "2");
  const box = await page.locator("#stage").boundingBox();
  await page.mouse.click(box.x + box.width * 0.7, box.y + box.height / 2);
  const v = +(await page.getAttribute("#handle", "aria-valuenow"));
  check(`${vp.name}: pointer moves slider`, Math.abs(v - 70) <= 2, `value=${v}`);
  const small = await page.evaluate(() => [...document.querySelectorAll("button,select,[role=slider],summary")]
    .filter(b => b.offsetParent).map(b => b.getBoundingClientRect()).filter(r => r.height < 44 || r.width < 36).length);
  check(`${vp.name}: visible controls ≥44 px tall`, small === 0, `${small} too small`);
  check(`${vp.name}: low-confidence pair starts uncorrected`, (await page.textContent("#badge")).includes("без коррекции"));
  await page.click("#alignBtn");
  check(`${vp.name}: toggle applies matrix3d + adjusted badge`, (await page.$eval("#photoLayer", e => e.style.transform)).includes("matrix3d")
    && (await page.textContent("#badge")).includes("скорректирована"));
  await shot(page, `${vp.name}-madeleine-aligned-attempt.jpg`);
  await page.click("#alignBtn");
  check(`${vp.name}: toggle back to original photo`, (await page.$eval("#photoLayer", e => e.style.transform)).startsWith("translate"));
  await page.click("#alignBtn");
  await page.click("[data-mode=opacity]");
  await shot(page, `${vp.name}-madeleine-opacity.jpg`);
  await page.click("[data-mode=sbs]");
  if (vp.name !== "ipad-820") await shot(page, `${vp.name}-madeleine-side-by-side.jpg`, { fullPage: vp.name !== "iphone-375" });
  check(`${vp.name}: all images have alt text`, await page.$$eval("img", ims => ims.every(i => i.alt && i.alt.length > 10)));
  const heads = await page.$$eval("h1,h2,h3,h4", hs => hs.map(h => h.tagName));
  check(`${vp.name}: heading levels do not skip (h1 → h2)`, heads[0] === "H1" && !heads.includes("H3") && !heads.includes("H4"), heads.join(","));
  // language toggle
  await page.click("[data-mode=slider]");
  await page.click("#langBtn");
  const en = await page.evaluate(() => ({ lang: document.documentElement.lang, badge: document.getElementById("badge").textContent,
    slider: document.querySelector("[data-mode=slider]").textContent, help: document.querySelector("#help summary").textContent,
    alt: document.getElementById("histImg").alt }));
  check(`${vp.name}: EN toggle switches labels, badge, alt text and lang attribute`, en.lang === "en" && en.slider === "Slider"
    && /^Photo (geometry adjusted|not corrected)/.test(en.badge) && en.help === "How to read the verdict" && en.alt.startsWith("Historic image"), JSON.stringify(en));
  await page.click("#help summary");
  const help = await page.evaluate(() => { const d = document.getElementById("help");
    const vis = [...d.querySelectorAll("[data-lang]")].filter(e => !e.hidden).map(e => e.dataset.lang); return { open: d.open, vis, txt: d.innerText }; });
  check(`${vp.name}: help explainer opens in the active language`, help.open && help.vis.join() === "en" && help.txt.includes("Leave-one-out") && help.txt.includes("viewpoint mismatch"));
  if (vp.name === "desktop-1440" || vp.name === "iphone-390") await shot(page, `${vp.name}-en-help.jpg`, { fullPage: vp.name === "iphone-390" });
  await page.reload({ waitUntil: "networkidle" });
  check(`${vp.name}: language choice remembered after reload`, (await page.evaluate(() => document.documentElement.lang)) === "en");
  await page.click("#langBtn");
  check(`${vp.name}: RU toggle back`, (await page.evaluate(() => document.documentElement.lang)) === "ru" && (await page.textContent("[data-mode=slider]")) === "Шторка");
  check(`${vp.name}: no console/page errors`, w.errors.length === 0, w.errors.join(" | "));
  check(`${vp.name}: no off-site requests`, w.offsite.length === 0, w.offsite.join(" "));
  await ctx.close();
}

async function robustnessChecks(browser) {
  // 1. noscript fallback
  let ctx = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  let page = await ctx.newPage();
  await page.goto(base, { waitUntil: "networkidle" });
  const ns = await page.evaluate(() => { const d = document.querySelector(".noscript");
    return d && d.offsetParent !== null ? [...d.querySelectorAll("a")].map(a => a.getAttribute("href")) : null; });
  check("noscript: fallback visible with links to both untouched originals",
    ns && ns.includes("pairs/madeleine-historic-loc-pga14315v.jpg") && ns.includes("pairs/palais-royal-photo-panoramax-200a3dee.jpg"));
  for (const href of ns || []) {
    const r = await page.request.get(new URL(href, base).href);
    if (!r.ok()) check(`noscript link ${href} resolves`, false, String(r.status()));
  }
  await shot(page, "iphone-390-noscript.jpg");
  await ctx.close();

  // 2. graceful image error
  ctx = await browser.newContext({ viewport: { width: 1024, height: 800 } });
  page = await ctx.newPage();
  const pe = [];
  page.on("pageerror", e => pe.push(String(e)));
  await page.route("**/pairs/madeleine-photo-panoramax-38b6d262.jpg", r => r.fulfill({ status: 404, body: "missing" }));
  await page.goto(`${base}#madeleine-ph-benoist`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => !document.getElementById("imgError").hidden, null, { timeout: 5000 }).catch(() => {});
  const ie = await page.evaluate(() => ({ visible: !document.getElementById("imgError").hidden, text: document.getElementById("imgError").textContent,
    link: !!document.querySelector("#imgError a[href='pairs/madeleine-photo-panoramax-38b6d262.jpg']"),
    hist: document.getElementById("histImg").naturalWidth > 0, credits: document.getElementById("creditBody").textContent.length > 50 }));
  check("image error: visible alert with a direct link, historic image and credits still shown", ie.visible && ie.link && ie.hist && ie.credits, ie.text);
  check("image error: no uncaught exceptions", pe.length === 0, pe.join(" | "));
  await shot(page, "desktop-1024-image-error.jpg");
  await ctx.close();

  // 3. hostile pair JSON: javascript: URLs and markup must not become live links/HTML; bogus ?mode= ignored
  ctx = await browser.newContext({ viewport: { width: 1024, height: 800 } });
  page = await ctx.newPage();
  const real = JSON.parse(fs.readFileSync(`${__dirname}/../../poc/compare/pairs/synthetic-near-identical.json`, "utf8"));
  const evil = { ...real, historic: { ...real.historic, object_url: "javascript:alert(1)", title: "<img src=x onerror=alert(2)>" },
    photo: { ...real.photo, license_url: "JaVaScRiPt:alert(3)", viewer_url: "data:text/html,hi" } };
  await page.route("**/pairs/synthetic-near-identical.json", r => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(evil) }));
  let dialogs = 0;
  page.on("dialog", d => { dialogs++; d.dismiss(); });
  await page.goto(`${base}?mode=bogus#synthetic-near-identical`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.getElementById("creditBody").textContent.length > 50);
  const sec = await page.evaluate(() => ({
    bad: [...document.querySelectorAll("a")].filter(a => !/^(https?:|pairs\/|editor\.html)/i.test(a.getAttribute("href") || "")).map(a => a.getAttribute("href")),
    injected: document.querySelectorAll("#creditBody img").length,
    mode: document.querySelector("[data-mode][aria-pressed=true]").dataset.mode }));
  check("security: no javascript:/data: links rendered from pair JSON", sec.bad.length === 0, sec.bad.join(" "));
  check("security: markup in JSON is escaped, not injected", sec.injected === 0 && dialogs === 0);
  check("security: invalid ?mode= falls back to slider", sec.mode === "slider");
  await ctx.close();
}

async function editorChecks(browser, vp) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile,
    hasTouch: !!vp.hasTouch, deviceScaleFactor: vp.deviceScaleFactor, acceptDownloads: true });
  const page = await ctx.newPage();
  const w = watch(page);
  page.on("dialog", d => d.accept());
  await page.goto(`${base}editor.html#madeleine-ph-benoist`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelectorAll("#ptTable tbody tr").length === 7 && document.getElementById("exportText").value.length > 100);
  const pair = JSON.parse(fs.readFileSync(`${__dirname}/../../poc/compare/pairs/madeleine-ph-benoist.json`, "utf8"));
  // 1. JS homography vs OpenCV
  const cmp = await page.evaluate((pair) => {
    const HG = window.CoPHomography, cp = pair.control_points;
    const H = HG.fitHomography(cp.map(c => c.photo), cp.map(c => c.historic));
    let worstPt = 0, worstGrid = 0;
    for (const c of cp) { const a = HG.project(H, c.photo), b = HG.project(pair.alignment.H, c.photo); worstPt = Math.max(worstPt, Math.hypot(a[0] - b[0], a[1] - b[1])); }
    for (let x = 0; x <= pair.photo.size[0]; x += 256) for (let y = 0; y <= pair.photo.size[1]; y += 256) {
      const a = HG.project(H, [x, y]), b = HG.project(pair.alignment.H, [x, y]); worstGrid = Math.max(worstGrid, Math.hypot(a[0] - b[0], a[1] - b[1])); }
    const ev = HG.evaluate(cp.map(c => c.photo), cp.map(c => c.historic), pair.historic.size, pair.photo.size);
    return { worstPt, worstGrid, rms: ev.rms_px, loo: ev.loo_max_px, conf: ev.confidence };
  }, pair);
  check(`${vp.name} editor: JS homography = OpenCV H on Madeleine control points (≤ 0.5 px)`, cmp.worstPt <= 0.5,
    `max ${cmp.worstPt.toFixed(5)} px on points, ${cmp.worstGrid.toFixed(4)} px on a photo-frame grid`);
  check(`${vp.name} editor: JS RMS / LOO / verdict match offline`, Math.abs(cmp.rms - pair.alignment.rms_px) < 0.01
    && Math.abs(cmp.loo - pair.alignment.loo_max_px) < 0.01 && cmp.conf === pair.alignment.confidence,
    `rms ${cmp.rms.toFixed(3)} loo ${cmp.loo.toFixed(3)} ${cmp.conf}`);
  const metrics = await page.textContent("#metrics");
  check(`${vp.name} editor: metrics panel shows the fit`, metrics.includes("RMS 6.55") && metrics.includes("LOO max 22.89"), metrics.slice(0, 120));
  // 2. export round-trip
  const ex1 = await page.$eval("#exportText", t => t.value);
  const p1 = JSON.parse(ex1);
  const sameCp = JSON.stringify(p1.control_points) === JSON.stringify(pair.control_points.map(c => ({ label: c.label, historic: c.historic, photo: c.photo })));
  check(`${vp.name} editor: export keeps control points, drops alignment, keeps sources`, sameCp && !("alignment" in p1)
    && p1.historic.sha256 === pair.historic.sha256 && p1.photo.license === pair.photo.license);
  await page.setInputFiles("#jsonFile", { name: "roundtrip.json", mimeType: "application/json", buffer: Buffer.from(ex1) });
  await page.waitForFunction(() => document.getElementById("status").textContent.includes("JSON"));
  const ex2 = await page.$eval("#exportText", t => t.value);
  check(`${vp.name} editor: export → import → export round-trips byte-identically`, ex1 === ex2);
  if (vp.name === "desktop-1440") {
    const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#exportBtn")]);
    const path = await dl.path();
    check(`${vp.name} editor: download is the same JSON (${dl.suggestedFilename()})`, fs.readFileSync(path, "utf8") === ex1);
  }
  // 3. pointer: add a point (historic then photo), drag it, delete it
  const n0 = await page.$$eval("#ptTable tbody tr", r => r.length);
  const boxOf = async (sel) => { await page.locator(sel).scrollIntoViewIfNeeded(); return page.locator(sel).boundingBox(); };
  const hv = await boxOf("#viewHist");
  await page.mouse.click(hv.x + hv.width * 0.1, hv.y + hv.height * 0.12);
  const expectPhoto = await page.evaluate(() => document.getElementById("panePhoto").classList.contains("expect"));
  const pv = await boxOf("#viewPhoto");
  await page.mouse.click(pv.x + pv.width * 0.1, pv.y + pv.height * 0.12);
  const n1 = await page.$$eval("#ptTable tbody tr", r => r.length);
  const added = JSON.parse(await page.$eval("#exportText", t => t.value)).control_points.slice(-1)[0];
  check(`${vp.name} editor: click historic → click photo adds one numbered pair`, expectPhoto && n1 === n0 + 1 && added && added.historic[0] > 0 && added.photo[0] > 0);
  const mk = page.locator(`#svgHist .mk[data-i="${n1 - 1}"] circle`);
  await page.locator("#viewHist").scrollIntoViewIfNeeded();
  const mb = await mk.boundingBox();
  await page.mouse.move(mb.x + mb.width / 2, mb.y + mb.height / 2);
  await page.mouse.down(); await page.mouse.move(mb.x + mb.width / 2 + 30, mb.y + mb.height / 2 + 20, { steps: 5 }); await page.mouse.up();
  const moved = JSON.parse(await page.$eval("#exportText", t => t.value)).control_points.slice(-1)[0];
  check(`${vp.name} editor: dragging a marker moves the point`, moved.historic[0] > added.historic[0] + 5 && moved.historic[1] > added.historic[1] + 3,
    `${added.historic} → ${moved.historic}`);
  // keyboard: nudge and delete the focused marker
  await page.focus(`#svgHist .mk[data-i="${n1 - 1}"]`);
  await page.keyboard.press("ArrowRight");
  const nudged = JSON.parse(await page.$eval("#exportText", t => t.value)).control_points.slice(-1)[0];
  check(`${vp.name} editor: ArrowRight on a focused marker nudges it 1 px`, Math.abs(nudged.historic[0] - moved.historic[0] - 1) < 0.11);
  await page.keyboard.press("Delete");
  check(`${vp.name} editor: Delete removes the focused point`, (await page.$$eval("#ptTable tbody tr", r => r.length)) === n0);
  // keyboard-only point: Enter in each pane
  await page.focus("#viewHist"); await page.keyboard.press("Enter");
  await page.focus("#viewPhoto"); await page.keyboard.press("Enter");
  check(`${vp.name} editor: keyboard Enter in both panes adds a point`, (await page.$$eval("#ptTable tbody tr", r => r.length)) === n0 + 1);
  await page.fill(`#ptTable input[data-i="${n0}"]`, "test label");
  check(`${vp.name} editor: label edits reach the export`, JSON.parse(await page.$eval("#exportText", t => t.value)).control_points.slice(-1)[0].label === "test label");
  await page.click(`[data-del="${n0}"]`);
  // zoom changes display size only
  await page.click('[data-zoom="hist"][data-k="1.5"]');
  const histImg = await page.evaluate(() => { const i = document.getElementById("imgHist"), cs = getComputedStyle(i);
    return { t: cs.transform, f: cs.filter, w: i.getBoundingClientRect().width }; });
  check(`${vp.name} editor: historic image zooms by size only (no transform/filter)`, histImg.t === "none" && histImg.f === "none" && histImg.w > 0);
  check(`${vp.name} editor: no horizontal page scroll`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  const small = await page.evaluate(() => [...document.querySelectorAll("header button, .pane button, main > .bar button, .filebtn, select")]
    .filter(b => b.offsetParent).map(b => b.getBoundingClientRect()).filter(r => r.height < 44).length);
  check(`${vp.name} editor: main controls ≥44 px tall`, small === 0, `${small} too small`);
  await page.click('[data-fit="hist"]');
  await page.goto(`${base}editor.html#madeleine-ph-benoist`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelectorAll("#ptTable tbody tr").length === 7);
  await page.waitForTimeout(200);
  await shot(page, `${vp.name}-editor-madeleine.jpg`, { fullPage: vp.name !== "desktop-1440" });
  check(`${vp.name} editor: no console/page errors`, w.errors.length === 0, w.errors.join(" | "));
  check(`${vp.name} editor: nothing requested outside the local server`, w.offsite.length === 0, w.offsite.join(" "));
  await ctx.close();
}

(async () => {
  for (const f of fs.readdirSync(outDir)) if (f.endsWith(".jpg")) fs.unlinkSync(`${outDir}/${f}`);
  const browser = await chromium.launch();
  for (const vp of viewports) await viewerChecks(browser, vp);
  await robustnessChecks(browser);
  for (const vp of viewports.filter(v => v.name === "iphone-390" || v.name === "desktop-1440")) await editorChecks(browser, vp);
  await browser.close();
  const failed = results.filter(r => !r.ok).length;
  fs.writeFileSync(`${outDir}/qa-results.json`, JSON.stringify({ when: new Date().toISOString(), passed: results.length - failed, failed, results }, null, 1));
  console.log(`\n${results.length - failed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
})();
