/* Responsive smoke and editorial journey for the source-backed museum salon. */
"use strict";
const {chromium}=require("playwright");
const [,,origin,outDir]=process.argv;
if(!origin||!outDir)throw Error("Expected museum origin and screenshot directory");
const fs=require("fs");fs.mkdirSync(outDir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  for(const [label,width,height] of [["phone",390,844],["tablet",820,1180],["desktop",1440,900]]){
   const page=await browser.newPage({viewport:{width,height}});
   const errors=[];page.on("pageerror",e=>errors.push(e.message));
   const salon=await page.goto(new URL("salon/",origin).href,{waitUntil:"domcontentloaded"});
   if(salon.status()!==200)throw Error("Salon is not served");
   await page.waitForFunction(()=>document.querySelectorAll(".art").length===41,{timeout:15000});
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error(label+": salon horizontal overflow");
   await page.locator("#query").fill("Пиранези");
   let n=await page.locator(".art").count();
   if(n<5||n>=41)throw Error(label+": search no-op ("+n+")");
   await page.locator("#query").fill("");
   await page.locator(".art").first().locator("button").click();
   await page.locator("#saved").click();
   if(await page.locator(".art").count()!==1)throw Error(label+": favorite not retained");
   await page.locator("#surprise").click();
   if(!await page.locator("#viewer").evaluate(n=>n.open))throw Error(label+": dialog does not open");
   await page.locator("#close").click();
   await page.screenshot({path:outDir+"/"+label+"-salon.jpg",type:"jpeg",quality:70,fullPage:true});
   const ex=await page.goto(new URL("exhibitions/city-as-evidence/",origin).href,{waitUntil:"domcontentloaded"});
   if(ex.status()!==200)throw Error("Exhibition not served");
   await page.waitForFunction(()=>document.querySelector("#image")?.getAttribute("src")?.length>8,{timeout:15000});
   if(await page.locator("#routes button").count()!==3)throw Error(label+": three routes missing");
   for(let j=0;j<2;j++)await page.locator("#next").click();
   if(await page.locator("#compare").isHidden())throw Error(label+": comparison not available at final artwork");
   await page.locator("#routes button").nth(1).click();
   if(!(await page.locator("#title").textContent()).includes("Сан-Марко"))throw Error(label+": Venice route missing");
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error(label+": exhibition horizontal overflow");
   await page.screenshot({path:outDir+"/"+label+"-exhibition.jpg",type:"jpeg",quality:70,fullPage:true});
   await page.goto(origin,{waitUntil:"domcontentloaded"});
   if(await page.locator('a[href="salon/"]').count()===0||await page.locator('a[href="exhibitions/city-as-evidence/"]').count()===0)throw Error(label+": home links missing");
   if(errors.length)throw Error(label+": runtime "+errors.join(" / "));
   console.log("PASS "+label+" salon, guided routes, comparison, responsive layout, home links");
   await page.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
