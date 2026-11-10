/* Hybrid museum — browser QA on source AND delivered package. */
"use strict";
const { chromium } = require("playwright");
const fs = require("fs");
const [,,base,out] = process.argv;
if (!base || !out) throw Error("Usage: qa_hybrid.js <origin> <screens>");
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const [device,w,h] of [["phone-390",390,844],["ipad-820",820,1180],["desktop-1440",1440,900]]){
   const context=await browser.newContext({viewport:{width:w,height:h},reducedMotion:"reduce"});
   const page=await context.newPage(),errs=[];
   page.on("pageerror",err=>errs.push(err.message));
   const home=await page.goto(new URL("./",base).href,{waitUntil:"domcontentloaded"});
   if(!home || home.status()!==200)throw Error(device+" homepage status "+home?.status());
   const first=await page.locator(".hybrid-story-hero a.btn.primary").getAttribute("href");
   if(first!=="stories/paris-on-paper/")throw Error(device+" wrong first CTA: "+first);
   if(await page.locator(".hybrid-story-hero h1").count()!==1)throw Error(device+" missing story-first headline");
   const hero=page.locator(".hybrid-story-hero .hybrid-hero-picture img");
   await hero.scrollIntoViewIfNeeded();
   await page.waitForFunction(()=>{const x=document.querySelector(".hybrid-hero-picture img");return x&&x.complete&&x.naturalWidth>150;},null,{timeout:17000});
   if(await page.locator(".hybrid-editorial-grid .hybrid-story-tile").count()!==3)throw Error(device+" no three curated cities");
   if(await page.locator(".hybrid-book-row a[href='experience/']").count()<1)throw Error(device+" missing optional book");
   if(await page.locator("a[href='atlas/']").count()<1)throw Error(device+" missing atlas");
   if(await page.locator("section#catalog").count()!==1)throw Error(device+" legacy catalog lost");
   let size=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));
   if(size.scroll>size.width+3)throw Error(device+" home horizontal overflow "+JSON.stringify(size));
   await page.screenshot({path:out+"/"+device+"-hybrid-home.jpg",type:"jpeg",quality:82,fullPage:false});
   const atlas=await page.goto(new URL("atlas/",base).href,{waitUntil:"domcontentloaded"});
   if(!atlas || atlas.status()!==200)throw Error(device+" atlas missing "+atlas?.status());
   await page.waitForFunction(()=>document.querySelectorAll(".result-item").length>=2,null,{timeout:20000});
   const count=await page.locator(".result-item").count();
   if(count<5)throw Error(device+" atlas too few real sources "+count);
   if(await page.locator("#selection").isHidden())throw Error(device+" initial real archival object hidden");
   await page.waitForFunction(()=>{const x=document.getElementById("selectedImage");return x&&x.complete&&x.naturalWidth>150;},null,{timeout:17000});
   if(!(await page.locator("#selectedSource").getAttribute("href")).startsWith("https://"))throw Error(device+" atlas lacks valid source");
   size=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));
   if(size.scroll>size.width+3)throw Error(device+" atlas horizontal overflow "+JSON.stringify(size));
   await page.screenshot({path:out+"/"+device+"-hybrid-atlas.jpg",type:"jpeg",quality:82,fullPage:false});
   await page.locator('button[data-city="florence"]').click();
   if((await page.locator("#currentCity").textContent()).indexOf("Флоренция")<0)throw Error(device+" Florence absent");
   await page.locator('button[data-era="print"]').click();
   const florenceRecords=await page.locator(".result-item").count();
   if(florenceRecords<1)throw Error(device+" Florence has no authentic print");
   await page.locator(".result-item").first().click();
   const source=await page.locator("#selectedSource").getAttribute("href");
   if(!source.includes("artic.edu"))throw Error(device+" expected AIC original but got "+source);
   const src=await page.locator("#selectedImage").getAttribute("src");
   if(!src.includes("florence_"))throw Error(device+" wrong historical city image "+src);
   await page.locator('button[data-city="naples"]').click();
   await page.locator('button[data-era="all"]').click();
   if((await page.locator("#resultCount").textContent()).includes("0 изображений"))throw Error(device+" Naples empty");
   if(await page.locator(".result-item").count()<2)throw Error(device+" Naples museum data missing");
   if(errs.length)throw Error(device+" JS errors "+JSON.stringify(errs));
   console.log("PASS "+device+": story-first home, atlas source, Florence print, Naples, zero page errors");
   await context.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
