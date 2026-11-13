/* Visitor-first museum: actual mobile layout and journey smoke test.
 * Run both at source preview and at final packaged public site.
 */
"use strict";
const {chromium}=require("playwright");
const [,,base]=process.argv;
if(!base)throw Error("Usage: qa_visitor_first.js <origin>");
function check(name,v){if(!v)throw Error(name);}
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [320,390,1440]){
   const context=await browser.newContext({viewport:{width,height:844},reducedMotion:"reduce"});
   const page=await context.newPage(),errors=[];
   page.on("pageerror",e=>errors.push(e.message));
   const go=async slug=>{
     const response=await page.goto(new URL(slug,base).href,{waitUntil:"domcontentloaded"});
     check(width+" "+slug+" responds 200",response?.status()===200);
   };
   await go("");
   check(width+" front door",await page.locator(".museum-frontdoor").count()===1);
   check(width+" global search",await page.locator("#frontQuery").count()===1);
   check(width+" visual time layers",await page.locator(".signature-pair img").count()===2);
   check(width+" editorial journal",await page.locator(".article-grid a").count()===3);
   check(width+" community invitation",await page.locator('.participate-home a[href="submit/"]').count()===1);
   check(width+" homepage no horizontal scrolling",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4));
   await go("walk/?city=paris");
   await page.waitForFunction(()=>document.querySelectorAll("#timeTrack .frame").length>2,null,{timeout:15000});
   check(width+" Paris modern photo",await page.locator("#newHeading").textContent()==="Современный вид");
   check(width+" Paris multi-era",await page.locator("#timeTrack .frame").count()>=3);
   check(width+" Paris picture files load",await page.evaluate(async()=>{
     const pics=[document.getElementById("oldImage"),document.getElementById("newImage")];
     await Promise.all(pics.map(x=>x.decode().catch(()=>{})));
     return pics.every(x=>x.naturalWidth>150);
   }));
   await page.locator('#cityButtons button[data-city="florence"]').click();
   check(width+" Florence no fake modern pair",await page.locator("#newHeading").textContent()==="Другой исторический год");
   check(width+" Florence comparison hidden",await page.locator("#pairRoute").isHidden());
   check(width+" Florence archive still browsable",await page.locator("#timeTrack .frame").count()>=2);
   check(width+" route no horizontal overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+4));
   await go("experience/");
   if((await page.locator("#atlasBook").getAttribute("data-open"))!=="true")await page.locator("#openBook").click();
   check(width+" book opened",await page.locator("#atlasBook").getAttribute("data-open")==="true");
   if(width<=390){
     const positions=await page.evaluate(()=>{
       const box=s=>document.querySelector(s).getBoundingClientRect();
       return {caption:box(".foldout-map figcaption"),expand:box("#mapOpen"),
         mapPage:box(".left-page"),chapters:box("#chapterList"),start:box("#startStory"),
         contents:box(".right-page")};
     });
     check(width+" map caption above expand button",positions.caption.bottom<=positions.expand.top+3);
     check(width+" map action inside first page",positions.expand.bottom<=positions.mapPage.bottom+3);
     check(width+" chapter list above read button",positions.chapters.bottom<=positions.start.top+3);
     check(width+" read button inside second page",positions.start.bottom<=positions.contents.bottom+3);
   }
   check(width+" book no horizontal overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+5));
   await go("salon/");
   await page.waitForFunction(()=>document.querySelectorAll("#gallery .art img").length>0,null,{timeout:18000});
   await page.locator("#gallery .art img").first().click();
   await page.locator("#viewer[open]").waitFor();
   const modal=await page.evaluate(()=>{
     const a=s=>{const r=document.querySelector(s).getBoundingClientRect();return {t:r.top,b:r.bottom,h:r.height,l:r.left,r:r.right}};
     return {dialog:a("#viewer"),tools:a(".viewerTools"),last:a("#viewer .viewerbar:last-child"),stage:a("#viewerStage"),
       reset:a("#zoomReset"),help:a(".viewerTools>span:last-child"),screen:innerHeight};
   });
   check(width+" viewer stage keeps real image space",modal.stage.h>=80);
   check(width+" zoom panel fits dialog",modal.tools.b<=modal.dialog.b+3);
   check(width+" source links fit dialog",modal.last.b<=modal.dialog.b+3);
   check(width+" help does not overlap zoom reset",
     modal.help.t>=modal.reset.b-2 || modal.help.l>=modal.reset.r-1);
   await page.locator("#close").click();
   await go("submit/");
   await page.locator("#city").fill("Париж, Франция");
   await page.locator("#title").fill("Церковь Мадлен");
   await page.locator("#suggestion button[type=submit]").click();
   check(width+" draft prepared not silently sent",await page.locator("#preview").isVisible());
   check(width+" issue handoff linked",String(await page.locator("#send").getAttribute("href")).startsWith("https://github.com/zukevich-blip/-city-on-paper/issues/new?"));
   check(width+" no JS runtime errors",errors.length===0);
   console.log("PASS Visitor first "+width+"px");
   await context.close();
  }
 }finally{await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1});
