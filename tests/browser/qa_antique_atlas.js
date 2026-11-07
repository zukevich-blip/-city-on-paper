"use strict";
// Test real navigation: nineteenth-century world map -> city -> museum print -> source/compare.
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const base=process.argv[2]||"http://127.0.0.1:8765/atlas-prototype/";
const out=process.argv[3]||"/tmp/city-on-paper-screens";
async function run(){
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const errors=[];
 try{
   const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
   page.on("pageerror",e=>errors.push(e.message));
   let response=await page.goto(base,{waitUntil:"domcontentloaded",timeout:20000});
   assert.equal(response.status(),200,"Atlas prototype HTTP 200");
   assert.match(await page.title(),/Исторический атлас/);
   await page.locator("#cityList button").first().waitFor();
   assert.equal(await page.locator("#atlasView").isVisible(),true);
   await page.locator("#cityList button").first().click();
   assert.equal(await page.locator("#cityName").textContent(),"Париж");
   assert.equal(await page.locator("#localMarkers button").count(),2);
   await page.locator("#localMarkers button").first().click();
   assert.equal(await page.locator("#modal").isVisible(),true);
   assert.match(await page.locator("#modalTitle").textContent(),/Мадлен/);
   assert.match(await page.locator("#modalSource").getAttribute("href"),/loc\.gov/);
   assert.match(await page.locator("#modalCompare").getAttribute("href"),/madeleine/);
   await page.locator("#modalImage").waitFor({state:"visible"});
   await page.locator("#closeModal").click();
   await page.locator("#backToAtlas").click();
   await page.locator("#citySearch").fill("Флоренция");
   assert.equal(await page.locator("#cityList button").count(),1);
   await page.locator("#cityList button").first().click();
   assert.equal(await page.locator("#cityName").textContent(),"Флоренция");
   await page.screenshot({path:path.join(out,"antique-atlas-florence-desktop.png"),fullPage:true});
   await page.close();
   const mobile=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true});
   mobile.on("pageerror",e=>errors.push(e.message));
   await mobile.goto(base+"?city="+encodeURIComponent("Париж"),{waitUntil:"domcontentloaded",timeout:20000});
   assert.equal(await mobile.locator("#cityName").textContent(),"Париж");
   assert.equal(await mobile.locator("#localMarkers button").count(),2);
   await mobile.screenshot({path:path.join(out,"antique-atlas-paris-mobile.png"),fullPage:true});
   const overflow=await mobile.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2);
   assert.equal(overflow,false,"No horizontal overflow at 390px");
   assert.deepEqual(errors,[],"No page JavaScript errors");
   console.log("PASS antique atlas: map -> city -> lithograph -> source; Florence; Paris mobile deep link");
 }finally{await browser.close()}
}
run().catch(e=>{console.error(e);process.exit(1)});
