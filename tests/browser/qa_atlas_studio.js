/* Browser QA: interactive map and private historical comparison studio. */
"use strict";
(async function auditAtlasStudio() {
  const { chromium } = require("playwright");
  const [, , origin] = process.argv;
  if (!origin) throw Error("Usage: qa_atlas_studio.js <site-origin>");
  const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+mPz8AAAAASUVORK5CYII=", "base64");
  function check(label, ok) { if (!ok) throw Error(label); }
  const browser = await chromium.launch({ headless: true });
  try {
    for (const width of [390,1440]) {
      const page = await browser.newPage({ viewport: { width, height: 844 }, acceptDownloads:true, reducedMotion:"reduce" });
      const errors = [];
      page.on("pageerror", (e) => errors.push(e.message));
      await page.goto(new URL("eras/#/",origin).href,{waitUntil:"domcontentloaded"});
      await page.waitForSelector("#pmap .mk",{timeout:18000});
      const count = (selector) => page.locator(selector).evaluateAll((markers) =>
        markers.reduce((sum, m) => sum + Number(m.dataset.count || 1),0));
      check(width+" historic markers available",(await count("#pmap .mk")) >= 150);
      check(width+" historic points clustered",(await page.locator("#pmap .city-cluster").count()) > 0);
      await page.locator("#tNew").click();
      await page.waitForSelector("#nmap .mk");
      check(width+" world covers geocoded atlas",(await count("#nmap .mk")) >= 180);
      check(width+" other map hidden",await page.locator("#pmap").isHidden());
      await page.locator("#q").fill("Париж");
      await page.waitForFunction(() => /Современная карта: 1 город/.test(document.querySelector("#mapSummary")?.textContent||""));
      check(width+" filter changes map",(await count("#nmap .mk"))===1);
      await page.locator("#mapWorld").click();
      check(width+" reset search",(await page.locator("#q").inputValue())==="");
      check(width+" all markers restored",(await count("#nmap .mk"))>=180);
      await page.locator("#mapArchive summary").click();
      await page.locator('[data-sheet="paris"]').click();
      check(width+" archive map selected",(await page.locator("#mapSheetImage").getAttribute("src")).includes("paris-1878"));
      check(width+" source linked",(await page.locator("#mapSheetSource").getAttribute("href")).includes("loc.gov/item/2012586603"));
      check(width+" no map horizontal overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4));
      await page.goto(new URL("eras/#/epochs",origin).href,{waitUntil:"domcontentloaded"});
      await page.waitForSelector("#epgal .epcard",{timeout:18000});
      await page.locator("#epgal .epcard").first().click();
      await page.waitForSelector("#epview .epstage");
      check(width+" four compare controls",(await page.locator("[data-compare-mode]").count())===4);
      await page.locator('[data-compare-mode="side"]').click();
      check(width+" side-by-side works",await page.locator("#epSide").isVisible() && await page.locator("#epstage").isHidden());
      await page.locator('[data-compare-mode="opacity"]').click();
      await page.locator("#epAmount").evaluate((el)=>{el.value="37";el.dispatchEvent(new Event("input",{bubbles:true}));});
      check(width+" opacity works",await page.locator("#epTop").evaluate((el)=>Math.abs(Number(el.style.opacity)-0.37)<0.02));
      await page.locator('[data-compare-mode="flip"]').click();
      await page.locator("#epFlipBtn").click();
      check(width+" A/B works",await page.locator("#epTop").evaluate((el)=>el.style.opacity==="1"));
      await page.locator('[data-compare-mode="slider"]').click();
      await page.locator("#epAdd").click();
      await page.locator("#epKind").selectOption("print");
      check(width+" historical upload needs no GPS",await page.locator("#epLocationGroup").isHidden());
      await page.locator("#epWorkYear").fill("1875");
      await page.locator("#epArtist").fill("Автор уточняется");
      await page.locator("#epSource").fill("https://www.loc.gov/");
      await page.locator("#epFile").setInputFiles({name:"private-historic.png",mimeType:"image/png",buffer:png});
      check(width+" file selected",await page.locator("#epSave").isEnabled());
      await page.locator("#epSave").click();
      await page.waitForFunction(()=>document.querySelectorAll("#epMine [data-del]").length>=1);
      check(width+" local upload stored",(await page.locator("#epMine").textContent()).includes("private-historic.png"));
      const downloadPromise=page.waitForEvent("download");
      await page.locator("#epExport").click();
      const download=await downloadPromise;
      check(width+" JSON export",download.suggestedFilename()==="city-on-paper-comparison.json");
      check(width+" no JS page errors",errors.length===0);
      console.log("PASS atlas comparison studio "+width+"px");
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(err=>{console.error(err);process.exitCode=1});
