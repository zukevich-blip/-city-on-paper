/* Browser verification of source-backed artwork study, iPad/phone layouts and private notes. */
"use strict";
const {chromium}=require("playwright");
const fs=require("fs");
const [,,origin,outDir]=process.argv;
if(!origin||!outDir)throw Error("Usage: qa_close_reading.js <origin> <screenshots>");
fs.mkdirSync(outDir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const [label,width,height] of [["phone",390,844],["ipad",820,1180],["desktop",1440,900]]){
   const context=await browser.newContext({viewport:{width,height}});
   const page=await context.newPage(),errors=[],writes=[];
   page.on("pageerror",e=>errors.push(e.message));
   page.on("request",r=>{if(!["GET","HEAD"].includes(r.method()))writes.push(r.method()+" "+r.url())});
   const response=await page.goto(new URL("closeup/?art=loc-2016652452",origin).href,{waitUntil:"domcontentloaded"});
   if(response.status()!==200)throw Error(label+": closeup HTTP"+response.status());
   await page.waitForFunction(()=>document.querySelector("#title")?.textContent?.includes("Мадлен"),{timeout:15000});
   if(await page.locator("#work option").count()!==11)throw Error(label+": 11 lessons missing");
   if(!(await page.locator("#licenseStatus").textContent()).includes("не CC0"))throw Error(label+": rights notice missing");
   await page.waitForFunction(()=>document.querySelector("#studyImage")?.naturalWidth>0,{timeout:15000});
   await page.screenshot({path:outDir+"/"+label+"-benoist-close-reading.jpg",type:"jpeg",quality:75,fullPage:true});
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error(label+": horizontal overflow");
   await page.locator("#zoomIn").click();
   if((await page.locator("#zoomLabel").textContent()).trim()!=="150%")throw Error(label+": zoom unavailable");
   await page.locator("#stage").scrollIntoViewIfNeeded();
   let bounds=await page.locator("#stage").boundingBox();
   await page.mouse.move(bounds.x+bounds.width*.52,bounds.y+bounds.height*.55);
   await page.mouse.down();await page.mouse.move(bounds.x+bounds.width*.62,bounds.y+bounds.height*.56,{steps:5});await page.mouse.up();
   let transform=await page.locator("#studyImage").evaluate(n=>n.style.transform);
   if(!transform.includes("translate(")||transform.includes("translate(0px,0px)"))throw Error(label+": dragging not registered");
   await page.locator("#reset").click();
   if((await page.locator("#zoomLabel").textContent()).trim()!=="100%")throw Error(label+": reset unavailable");
   await page.locator("#next").click();
   if(!(await page.locator("#stepName").textContent()).includes("2 из 3"))throw Error(label+": study stages broken");
   await page.locator("#work").selectOption("cma-1922-225");
   if(!(await page.locator("#licenseStatus").textContent()).includes("CC0"))throw Error(label+": CMA source label missing");
   await page.locator("#notes").fill("Повторяющиеся арки создают ощущение масштаба.");
   await page.reload({waitUntil:"domcontentloaded"});
   await page.waitForFunction(()=>document.querySelector("#title")?.textContent?.includes("Колизей"),{timeout:15000});
   if(!(await page.locator("#notes").inputValue()).includes("арки"))throw Error(label+": personal note did not persist");
   await page.locator("#clearNotes").click();
   if((await page.locator("#notes").inputValue())!=="")throw Error(label+": user cannot clear note");
   await page.screenshot({path:outDir+"/"+label+"-close-reading.jpg",type:"jpeg",quality:70,fullPage:true});
   await page.goto(new URL("salon/",origin).href,{waitUntil:"domcontentloaded"});
   await page.waitForFunction(()=>document.querySelector('a[href="../closeup/?art=cma-1922-225"]'),{timeout:15000});
   await page.goto(new URL("exhibitions/city-as-evidence/",origin).href,{waitUntil:"domcontentloaded"});
   await page.waitForFunction(()=>document.querySelector("#closeupLink")?.getAttribute("href")?.includes("cma-1922-225"),{timeout:15000});
   await page.goto(origin,{waitUntil:"domcontentloaded"});
   if(await page.locator('a[href="closeup/"]').count()===0)throw Error(label+": front-door link absent");
   if(errors.length||writes.length)throw Error(label+": JS/runtime or unexpected POST requests "+JSON.stringify({errors,writes}));
   console.log("PASS "+label+" museum close reading, attribution, pan, zoom, study notes, links");
   await context.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
