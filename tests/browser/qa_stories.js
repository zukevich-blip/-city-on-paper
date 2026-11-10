/* The new editorial entry must work on the actual packaged museum as well as source. */
"use strict";
const { chromium } = require("playwright");
const fs = require("fs");
const [,,base,outDir] = process.argv;
if (!base || !outDir) throw Error("Usage: qa_stories.js <base-url> <screenshots-directory>");
fs.mkdirSync(outDir,{recursive:true});
(async()=>{
 const browser = await chromium.launch({headless:true});
 try{
  for(const [label,w,h] of [["phone-390",390,844],["desktop-1440",1440,900]]){
   const context=await browser.newContext({viewport:{width:w,height:h}});
   const page=await context.newPage(),errors=[];
   page.on("pageerror",e=>errors.push(e.message));
   for(const [route,file] of [["stories/","hub"],["stories/paris-on-paper/","paris"]]){
    const url=new URL(route,base).href;
    const response=await page.goto(url,{waitUntil:"domcontentloaded"});
    if(!response || response.status()!==200)throw Error(label+" missing "+route+": "+response?.status());
    const headings=await page.locator("h1").count();
    if(headings!==1)throw Error(label+" "+route+": expected one H1, got "+headings);
    const overflow=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));
    if(overflow.scroll>overflow.width+2)throw Error(label+" "+route+": horizontal overflow "+JSON.stringify(overflow));
    const img=page.locator("main img").first();
    await img.scrollIntoViewIfNeeded();
    await page.waitForFunction(()=>{const n=document.querySelector("main img");return n instanceof HTMLImageElement&&n.complete&&n.naturalWidth>200;},null,{timeout:15000});
    const sourceLinks=await page.locator('a[href*="loc.gov/item/"]').count();
    if(sourceLinks<1)throw Error(label+" "+route+": missing LoC primary-source links");
    const badAlt=await page.locator("img:not([alt]),img[alt='']").count();
    if(badAlt)throw Error(label+" "+route+": "+badAlt+" images missing alt");
    if(errors.length)throw Error(label+" "+route+": "+JSON.stringify(errors));
    await page.screenshot({path:outDir+"/"+label+"-story-"+file+".jpg",type:"jpeg",quality:78,fullPage:false});
    console.log("PASS "+label+" "+route+": readable, no overflow, genuine local image and LoC source");
   }
   await context.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
