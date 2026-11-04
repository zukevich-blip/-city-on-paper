/* Validate the published artifact, not the repository source tree. */
"use strict";
const { chromium } = require("playwright");
const fs = require("fs");
const [,,base,outDir]=process.argv;
if(!base||!outDir)throw Error("Usage: qa_packaged.js <http-origin> <screenshots-directory>");
fs.mkdirSync(outDir,{recursive:true});
const paths=["","salon/","photography/","closeup/","exhibitions/city-as-evidence/","poc/compare/","fieldwork/",
 "journeys/","detective/","discover/","studio/","ideas/","printlab/","ornaments/","atelier/bargue/","atelier/ornament/"];
async function requireImage(page,id,min=80){await page.waitForFunction(({selector,min})=>{const n=document.querySelector(selector);return n instanceof HTMLImageElement&&n.complete&&n.naturalWidth>=min;},{selector:id,min},{timeout:22000})}
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const [label,w,h] of [["phone-390",390,844],["ipad-820",820,1180],["desktop-1440",1440,900]]){
   const c=await browser.newContext({viewport:{width:w,height:h}}),p=await c.newPage(),errs=[];
   p.on("pageerror",e=>errs.push(e.message));
   for(const path of paths){const resp=await p.goto(new URL(path,base).href,{waitUntil:"domcontentloaded"});
    if(!resp||resp.status()!==200)throw Error(label+": missing "+path+": "+resp?.status());
    const overflow=await p.evaluate(()=>({scroll:document.documentElement.scrollWidth,view:innerWidth,offenders:[...document.querySelectorAll("body *")].filter(e=>{let r=e.getBoundingClientRect();return r.width>0&&r.right>innerWidth+3}).slice(0,6).map(e=>({tag:e.tagName,cls:typeof e.className==="string"?e.className.slice(0,60):"",id:e.id,right:Math.round(e.getBoundingClientRect().right)}))}));if(overflow.scroll>overflow.view+2)throw Error(label+": horizontal overflow "+path+" "+JSON.stringify(overflow));
   }
   await p.goto(new URL("salon/",base).href,{waitUntil:"domcontentloaded"});
   await p.waitForFunction(()=>document.querySelectorAll("#gallery .art").length>=41,{timeout:15000});
   await p.waitForFunction(()=>document.querySelector("#archiveStatus")?.textContent?.includes("Расширенный фонд:"),{timeout:25000});
   const countLine=await p.locator("#count").textContent();const n=Number(countLine.split(" · ").find(x=>x.includes("архивных находок"))?.split(" ")[0]||0);if(n<60)throw Error(label+": expanded visible museum artworks only "+n);
   await requireImage(p,"#gallery .art img");
   await p.screenshot({path:outDir+"/"+label+"-artifact-salon.jpg",type:"jpeg",quality:70});
   await p.goto(new URL("photography/",base).href,{waitUntil:"domcontentloaded"});
   await p.waitForFunction(()=>document.querySelectorAll(".gallery .photo").length>=4,{timeout:15000});
   const photoCredits=await p.locator(".gallery .photo .links a").count();if(photoCredits<8)throw Error(label+": photo sources or license credits missing");
   await requireImage(p,".gallery .photo img");
   await p.screenshot({path:outDir+"/"+label+"-artifact-modern-photos.jpg",type:"jpeg",quality:70});
   await p.goto(new URL("exhibitions/city-as-evidence/",base).href,{waitUntil:"domcontentloaded"});
   await requireImage(p,"#image");
   await p.locator("#routes button").nth(1).click();await requireImage(p,"#image");
   await p.screenshot({path:outDir+"/"+label+"-artifact-venice.jpg",type:"jpeg",quality:70});
   await p.goto(new URL("closeup/?art=loc-2016652452",base).href,{waitUntil:"domcontentloaded"});
   await requireImage(p,"#studyImage",500);
   const notice=await p.locator("#licenseStatus").textContent();if(!notice.includes("не CC0"))throw Error(label+": Benoist rights notice missing");
   await p.screenshot({path:outDir+"/"+label+"-artifact-benoist.jpg",type:"jpeg",quality:70});
   await p.goto(new URL("poc/compare/",base).href,{waitUntil:"domcontentloaded"});
   await requireImage(p,"#histImg");await requireImage(p,"#photoImg");
   const slider=p.locator("#handle");await slider.focus();
   const before=Number(await slider.getAttribute("aria-valuenow"));
   await p.keyboard.press("ArrowRight");
   const after=Number(await slider.getAttribute("aria-valuenow"));
   if(!(after>before))throw Error(label+": historic/modern slider keyboard movement failed");
   await p.locator('[data-mode="sbs"]').click();
   if(await p.locator("#sbs").isHidden())throw Error(label+": side by side mode broken");
   await p.screenshot({path:outDir+"/"+label+"-artifact-then-now.jpg",type:"jpeg",quality:70});
   if(errs.length)throw Error(label+": JS runtime errors: "+errs.slice(0,5).join(" / "));
   await c.close();
   console.log("PASS "+label+": 16 routes + museum expansion + modern photos + Benoist + source slider");
  }
 }finally{await browser.close()}
})().catch(err=>{console.error(err);process.exitCode=1});
