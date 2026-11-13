/* Verify that the public-facing world -> city -> artwork journey stays navigable.
 * Run against both source checkout and actual packaged release.
 */
"use strict";
const {chromium}=require("playwright");
const [,,base]=process.argv;
if(!base)throw Error("Usage: qa_unified_journey.js <origin>");
function assert(label,ok){if(!ok)throw Error(label);}
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [390,1440]){
   const context=await browser.newContext({viewport:{width,height:844},reducedMotion:"reduce"});
   const page=await context.newPage(),errors=[];
   page.on("pageerror",e=>errors.push(e.message));
   const go=async path=>{
     const resp=await page.goto(new URL(path,base).href,{waitUntil:"domcontentloaded"});
     assert(width+" "+path+" HTTP 200",resp?.status()===200);
     await page.waitForSelector("#museumBar");
     assert(width+" all-rooms menu available",await page.locator("#museumBar button").isVisible());
     assert(width+" all-rooms panel initially hidden",await page.locator("#museumPanel").isHidden());
   };
   await go("cities/?query=%D0%A4%D0%BB%D0%BE%D1%80%D0%B5%D0%BD%D1%86%D0%B8%D1%8F");
   await page.waitForFunction(()=>document.querySelectorAll(".city-card").length>0);
   assert(width+" city query deep link",await page.locator("#query").inputValue()==="Флоренция");
   assert(width+" Florence atlas route",await page.locator('.city-card a[href="../atlas/?city=florence"]').count()===1);
   assert(width+" Florence gallery route",await page.locator('.city-card a[href*="../salon/?city="]').count()>=1);
   assert(width+" no fictional Florence comparison",await page.locator('.city-card a[href*="compare/"]').count()===0);
   await page.locator("#museumBar button").click();
   assert(width+" menu opens",await page.locator("#museumPanel").isVisible());
   assert(width+" compare accessible",await page.locator('#museumPanel a[href$="poc/compare/"]').count()===1);
   await page.locator("#museumBar button").click();
   assert(width+" menu closes",await page.locator("#museumPanel").isHidden());
   await go("atlas/?city=florence");
   await page.waitForFunction(()=>document.querySelector("#routeCity")?.href.includes("query="));
   assert(width+" route goes to Florence",await page.locator("#routeCity").getAttribute("href")===
     "../cities/?query="+encodeURIComponent("Флоренция"));
   assert(width+" no unchecked comparison",await page.locator("#routeCompare").isHidden());
   await page.locator('#cityFilters [data-city="paris"]').click();
   assert(width+" Paris comparison available",await page.locator("#routeCompare").isVisible());
   await go("world/?query=%D0%9F%D0%B0%D1%80%D0%B8%D0%B6");
   assert(width+" world search retains route",await page.locator("#query").inputValue()==="Париж");
   assert(width+" no horizontal overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4));
   assert(width+" no browser runtime errors",errors.length===0);
   console.log("PASS unified city journey, width "+width);
   await context.close();
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
