"use strict";
(async function auditConsiliumControls(){
 const {chromium}=require("playwright");
 const root=process.argv[2]||"http://127.0.0.1:8791/";
 const browser=await chromium.launch({headless:true});
 try{
  for(const w of [390,820,1440]){
   const ctx=await browser.newContext({viewport:{width:w,height:850},isMobile:w===390,hasTouch:w===390});
   const page=await ctx.newPage(),errors=[];
   page.on("pageerror",e=>errors.push(e.message));
   await page.goto(new URL("salon/",root).href,{waitUntil:"domcontentloaded"});
   await page.waitForSelector("#museumBar");
   const btn=page.locator('#museumBar button[aria-controls="museumPanel"]');
   if(await page.locator("#museumPanel").isVisible())throw Error("panel unexpectedly open");
   await btn.click();
   if(!(await page.locator("#museumPanel").isVisible()))throw Error("menu cannot open "+w);
   await page.locator("header h1").click();
   if(!(await page.locator("#museumPanel").isHidden()))throw Error("menu cannot close outside "+w);
   await btn.click();
   await page.keyboard.press("Escape");
   if(!(await page.locator("#museumPanel").isHidden()))throw Error("Escape cannot close menu "+w);
   const back=page.locator("#museumBack");
   if(!(await back.getAttribute("href")).includes("/-city-on-paper/")&&!(await back.getAttribute("href")).endsWith("/"))throw Error("back doesn't point to museum");
   await page.locator("#query").fill("Париж");
   if(await page.locator("#toggleFilters").isVisible())await page.locator("#toggleFilters").click();
   await page.locator("#scope").selectOption("curated");
   await page.locator("#resetFilters").click();
   if(await page.locator("#query").inputValue())throw Error("reset failed search");
   if(await page.locator("#scope").inputValue()!=="all")throw Error("reset failed scope");
   if((await page.locator("#toggleFilters").innerText()).includes("· 1"))throw Error("active filter badge not cleared");
   await page.waitForFunction(()=>document.querySelectorAll("#gallery .art").length>0,{timeout:15000}).catch(async()=>await page.waitForSelector("#gallery .art",{timeout:15000}));
   if(!(await page.locator('#gallery a[href*="/eras/"]').count()))throw Error("salon has no direct atlas links "+w);
   await page.goto(new URL("eras/",root).href,{waitUntil:"domcontentloaded"});
   await page.waitForSelector("#pmap .mk",{timeout:18000});
   await page.locator("#mapArchiveOpen").click();
   if(!(await page.locator("#mapArchive").evaluate(x=>x.open)))throw Error("archives not expanded");
   await page.locator('[data-sheet="paris"]').click();
   if(!(await page.locator("#mapSheetImage").getAttribute("src")).includes("paris-1878"))throw Error("Paris sheet not changed");
   if(w===390){
    const height=await page.locator("#pmap").evaluate(el=>el.getBoundingClientRect().height);
    if(height>440)throw Error("historical map still oversized on iPhone: "+height);
   }
   if(errors.length)throw Error("JS errors "+w+": "+errors.slice(0,3).join("; "));
   console.log("PASS independent controls "+w+"px");
   await ctx.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
