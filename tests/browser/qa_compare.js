// Browser QA for poc/compare. Usage: node tests/browser/qa_compare.js http://127.0.0.1:8765/poc/compare/ docs/screens
const { chromium } = require("playwright");
const [, , base, outDir] = process.argv;
const viewports = [
  { name: "iphone-375", width: 375, height: 812, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
  { name: "iphone-390", width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
  { name: "ipad-820", width: 820, height: 1180, isMobile: true, hasTouch: true, deviceScaleFactor: 1 },
  { name: "desktop-1440", width: 1440, height: 900, deviceScaleFactor: 1 },
];
const results = [];
const check = (name, ok, detail = "") => { results.push({ name, ok, detail }); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail}`); };

(async () => {
  const browser = await chromium.launch();
  for (const vp of viewports) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile,
      hasTouch: !!vp.hasTouch, deviceScaleFactor: vp.deviceScaleFactor, reducedMotion: vp.name === "iphone-375" ? "reduce" : "no-preference" });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(String(e)));
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    for (const id of ["madeleine-ph-benoist", "synthetic-near-identical", "synthetic-rotation-only", "synthetic-parallax"]) {
      await page.goto(`${base}?split=55#${id}`, { waitUntil: "networkidle" });
      await page.waitForFunction((id) => document.getElementById("pairSel").value === id &&
        document.getElementById("histImg").complete && document.getElementById("photoLayer").style.transform !== "" &&
        document.getElementById("credits").textContent.length > 50, id);
      await page.waitForTimeout(150);
      const evidence = await page.evaluate(async (id) => {
        const a = (await (await fetch(`pairs/${id}.json`)).json()).alignment;
        return { confidence: a.confidence, coverage: a.control_point_coverage ?? 0 };
      }, id);
      const conf = evidence.confidence;
      const safeInitial = !["high", "medium"].includes(conf) || evidence.coverage < 0.15;
      if (safeInitial) {
        check(`${vp.name} ${id}: '${conf}' opens with the untouched photo`,
          (await page.$eval("#photoLayer", e => e.style.transform)).startsWith("translate"));
        await page.click("#alignBtn");
      }
      if (id === "madeleine-ph-benoist") {
        check(`${vp.name} Madeleine: small coverage is stated explicitly`,
          (await page.textContent("#verdict")).includes("7%"));
      }
      // math check: CSS transform of the photo layer must send each photo control point onto its historic point
      const err = await page.evaluate(async (id) => {
        const pair = await (await fetch(`pairs/${id}.json`)).json();
        if (!pair.alignment || !pair.alignment.H) return null;
        const L = document.getElementById("photoLayer"), st = document.getElementById("stage");
        const m = new DOMMatrix(getComputedStyle(L).transform);
        const s = st.clientWidth / pair.historic.size[0];
        let worst = 0;
        for (const c of pair.control_points) {
          const p = m.transformPoint(new DOMPoint(c.photo[0], c.photo[1], 0, 1));
          const x = p.x / p.w, y = p.y / p.w;
          const dx = x / s - c.historic[0], dy = y / s - c.historic[1];
          const r = Math.hypot(dx, dy), expected = pair.alignment.residuals_px[pair.control_points.indexOf(c)];
          worst = Math.max(worst, Math.abs(r - expected));
        }
        return worst;
      }, id);
      if (err !== null) check(`${vp.name} ${id}: CSS matrix3d reproduces offline residuals`, err < 0.1, `max |Δ| = ${err.toFixed(4)} px`);
      const exclusive = await page.evaluate(() => {
        const vis = (id) => getComputedStyle(document.getElementById(id)).display !== "none";
        return vis("stage") && !vis("sbs");
      });
      check(`${vp.name} ${id}: slider mode hides side-by-side panel`, exclusive);
      const histUntouched = await page.evaluate(() => {
        const h = document.getElementById("histImg"); const cs = getComputedStyle(h);
        return cs.transform === "none" && cs.filter === "none" && h.naturalWidth > 0;
      });
      check(`${vp.name} ${id}: historic image has no transform/filter`, histUntouched);
      const noHScroll = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
      check(`${vp.name} ${id}: no horizontal page scroll`, noHScroll);
      if (id === "madeleine-ph-benoist" || vp.name === "desktop-1440")
        await page.screenshot({ path: `${outDir}/${vp.name}-${id}-slider.jpg`, type: "jpeg", quality: 70, fullPage: vp.name !== "desktop-1440" });
    }
    // interactions on the real pair
    await page.goto(`${base}#madeleine-ph-benoist`, { waitUntil: "networkidle" });
    await page.waitForFunction(() => document.getElementById("photoLayer").style.transform !== "");
    check(`${vp.name}: Madeleine starts with unmodified photo`,
      (await page.$eval("#photoLayer", e => e.style.transform)).startsWith("translate"));
    await page.click("#alignBtn");
    check(`${vp.name}: explicit alignment turns on corrected photo`,
      (await page.$eval("#photoLayer", e => e.style.transform)).includes("matrix3d"));
    await page.focus("#handle"); await page.keyboard.press("Home");
    check(`${vp.name}: keyboard Home moves slider to 0`, (await page.getAttribute("#handle", "aria-valuenow")) === "0");
    await page.keyboard.press("ArrowRight");
    check(`${vp.name}: ArrowRight steps slider`, (await page.getAttribute("#handle", "aria-valuenow")) === "2");
    const box = await page.locator("#stage").boundingBox();
    await page.mouse.click(box.x + box.width * 0.7, box.y + box.height / 2);
    const v = +(await page.getAttribute("#handle", "aria-valuenow"));
    check(`${vp.name}: pointer moves slider`, Math.abs(v - 70) <= 2, `value=${v}`);
    const sizes = await page.evaluate(() => [...document.querySelectorAll("button,select,[role=slider]")]
      .filter(b => b.offsetParent).map(b => b.getBoundingClientRect()).filter(r => r.height < 44 || r.width < 36).length);
    check(`${vp.name}: visible controls ≥44 px tall`, sizes === 0, `${sizes} too small`);
    await page.click("#alignBtn");
    check(`${vp.name}: toggle to original photo removes matrix3d`, (await page.$eval("#photoLayer", e => e.style.transform)).startsWith("translate"));
    check(`${vp.name}: badge says uncorrected`, (await page.textContent("#badge")).includes("без коррекции"));
    await page.click("#alignBtn");
    await page.click("[data-mode=opacity]");
    await page.screenshot({ path: `${outDir}/${vp.name}-madeleine-opacity.jpg`, type: "jpeg", quality: 70 });
    await page.click("[data-mode=sbs]");
    await page.screenshot({ path: `${outDir}/${vp.name}-madeleine-side-by-side.jpg`, type: "jpeg", quality: 70, fullPage: true });
    const alts = await page.$$eval("img", ims => ims.every(i => i.alt && i.alt.length > 10));
    check(`${vp.name}: all images have alt text`, alts);
    check(`${vp.name}: no console/page errors`, errors.length === 0, errors.join(" | "));
    await ctx.close();
  }
  await browser.close();
  const failed = results.filter(r => !r.ok).length;
  require("fs").writeFileSync(`${outDir}/qa-results.json`, JSON.stringify({ when: new Date().toISOString(), passed: results.length - failed, failed, results }, null, 1));
  console.log(`\n${results.length - failed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
})();
