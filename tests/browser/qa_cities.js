/* Source + packaged browser QA: verify real world city index and mobile usability. */
"use strict";
const { chromium }=require("playwright");
const fs=require("fs");
const [,,base,output]=process.argv;
if(!base || !output) throw Error("Usage: qa_cities.js <origin> <screenshot-dir>");
fs.mkdirSync(output,{recursive:true});
function check(name,condition){if(!condition)throw Error(name);}
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  for(const [device,width,height] of [["phone-320",320,750],["phone-390",390,844],["ipad-820",820,1180],["desktop-1440",1440,900]]){
   const ctx=await browser.newContext({viewport:{width,height},reducedMotion:"reduce"});
   const page=await ctx.newPage(),errors=[];
   page.on("pageerror",e=>errors.push(e.message));
   const home=await page.goto(new URL("./",base).href,{waitUntil:"domcontentloaded"});
   check(device+" home loaded",home && home.status()===200);
   await page.waitForSelector('.hybrid-story-hero a.btn.primary[href="stories/paris-on-paper/"]');
   check(device+" cities visible on home",await page.locator('header .navlinks a[href="cities/"]').count()===1);
   const menu=page.locator("header .navlinks");
   await menu.scrollIntoViewIfNeeded();
   const desktopNav=await menu.boundingBox();
   check(device+" main nav compact",!desktopNav || desktopNav.height < 110);
   const firstTitle=await page.locator(".hybrid-story-hero h1").textContent();
   check(device+" story-first home",firstTitle.includes("Париж"));
   const response=await page.goto(new URL("cities/",base).href,{waitUntil:"domcontentloaded"});
   check(device+" city index status",response && response.status()===200);
   await page.waitForFunction(()=>document.querySelectorAll(".city-card").length>5,null,{timeout:18000});
   const total=await page.locator("#coverageStats .stat strong").first().textContent();
   const n=Number(total);
   check(device+" city registry size",n>=150 && n<=300);
   await page.waitForFunction(()=>{const n=document.querySelector(".hero-art-grid img");return n?.complete&&n.naturalWidth>150},null,{timeout:18000});
   const size=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth}));
   check(device+" city page no overflow",size.scroll<=size.viewport+3);
   await page.screenshot({path:output+"/"+device+"-world-cities.jpg",type:"jpeg",quality:83,fullPage:false});
   await page.locator("#query").fill("Флоренция");
   await page.waitForTimeout(100);
   const florence=page.locator(".city-card");
   check(device+" query filtered",await florence.count()===1);
   check(device+" Florence detailed",((await florence.first().textContent())||"").includes("Флоренция"));
   check(device+" Florence source route",await florence.locator('a[href="../atlas/?city=florence"]').count()===1);
   await page.locator("#reset").click();
   await page.locator("#status").selectOption("detailed");
   await page.waitForTimeout(70);
   check(device+" detailed has three cities",await page.locator(".city-card").count()===3);
   await page.locator("#type").selectOption("place");
   await page.waitForTimeout(80);
   check(device+" no invented place exhibitions",await page.locator(".city-card").count()===0);
   await page.locator("#reset").click();
   await page.locator("#query").fill("Санкт-Петербург");
   await page.waitForTimeout(80);
   check(device+" St Petersburg query exists",await page.locator(".city-card").count()>=1);
   check(device+" no fabricated St Petersburg story",await page.locator('.city-card a[href*="atlas/?city=petersburg"]').count()===0);
   check(device+" no runtime errors",errors.length===0);
   console.log("PASS "+device+": global city directory "+n+" entries, authentic provenance, filtering and responsive UI");
   await ctx.close();
  }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
