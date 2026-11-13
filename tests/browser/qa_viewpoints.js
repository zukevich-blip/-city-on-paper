/* Evidence-aware viewpoint atlas QA at iPhone and desktop widths. */
"use strict";
const { chromium } = require("playwright");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const base=(process.argv[2]||"http://127.0.0.1:8765/").replace(/\/?$/,"/");
const output=process.argv[3]||"/tmp/city-on-paper-screens";
(async()=>{
  fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
  try {
    for(const width of [390,1440]) {
      const context=await browser.newContext({viewport:{width,height:845}});
      const page=await context.newPage();
      const errors=[];
      page.on("pageerror",e=>errors.push(e.message));
      await page.goto(base+"eras/#/city/paris",{waitUntil:"domcontentloaded"});
      await page.locator("#vpaGallery .vpa-art").first().waitFor({timeout:25000});
      assert(await page.locator("#vpaOld").count(),"Named Paris 1878 detail map");
      assert(await page.locator("#vpaNow.leaflet-container").count(),"Modern city map");
      assert((await page.locator("#vpaGallery .vpa-art").count())>=4,"Archive cards");
      assert(await page.locator("#vpaStatus").textContent()!=="","Viewpoint status");
      const selected=await page.locator("#vpaSelected").textContent();
      assert(selected && selected.length>3,"Selected artwork");
      const callout=(await page.locator("#vpaCompareTruth").textContent()).toLowerCase();
      assert(/ракурс|перспектив|пара/.test(callout),"Scientific caution about angles");
      await page.locator("#vpaWipe").click();
      assert.equal(await page.locator("#vpaWipe").getAttribute("aria-pressed"),"true");
      assert(await page.locator("#vpaCompare.is-wipe").count(),"Wipe interaction");
      await page.locator("#vpaSide").click();
      assert(await page.locator("#vpaCompare:not(.is-wipe)").count(),"Side mode");
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+5),"No horizontal overflow");
      if(width===390) {
        const priorMarkers=await page.locator("#vpaNow .leaflet-overlay-pane path").count();
        await page.locator("#vpaContribution summary").click();
        await page.locator("#vpaLink").selectOption("loc-2016652452");
        await page.locator("#vpaLat").fill("48.8694");
        await page.locator("#vpaLon").fill("2.3236");
        await page.locator("#vpaAz").fill("45");
        await page.locator("#vpaFile").setInputFiles({
          name:"mine-viewpoint.png",mimeType:"image/png",
          buffer:Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==","base64")
        });
        await page.locator("#vpaSave").click();
        await page.waitForFunction(()=>/сохранён/.test(document.querySelector("#vpaFeedback")?.textContent||""));
        assert.equal((await page.locator("#vpaOwnCount").textContent()).trim(),"1");
        assert((await page.locator("#vpaNow .leaflet-overlay-pane path").count())>priorMarkers,"New personal geo marker after save");
        await page.reload({waitUntil:"domcontentloaded"});
        await page.locator("#vpaOwnCount").waitFor();
        await page.waitForFunction(()=>document.querySelector("#vpaOwnCount")?.textContent==="1");
        assert.equal((await page.locator("#vpaOwnCount").textContent()).trim(),"1","Private photo preserved");
      }
      await page.screenshot({path:path.join(output,"viewpoint-"+width+".png"),fullPage:true});
      assert.equal(errors.length,0,"No uncaught JS errors: "+errors.join(" | "));
      console.log("PASS viewpoint atlas "+width+"px, old/new maps, provenance, slider, private geo photo");
      await context.close();
    }
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});