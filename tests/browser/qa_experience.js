/* Book of Cities: source + packaged Chromium smoke, no remote dependencies. */
"use strict";
const { chromium } = require("playwright");
const fs = require("fs");
const [,,base,output] = process.argv;
if (!base || !output) throw Error("Usage: qa_experience.js <origin> <screenshots-dir>");
fs.mkdirSync(output,{recursive:true});
(async()=>{
  const browser = await chromium.launch({headless:true});
  try {
    for(const [name,width,height] of [["phone-390",390,844],["ipad-820",820,1180],["desktop-1440",1440,900]]) {
      const context=await browser.newContext({viewport:{width,height},reducedMotion:"no-preference"});
      const page=await context.newPage(), errors=[];
      page.on("pageerror",e=>errors.push(e.message));
      const url=new URL("experience/",base).href;
      const response=await page.goto(url,{waitUntil:"domcontentloaded"});
      if(!response||response.status()!==200)throw Error(name+" book missing "+response?.status());
      const wrap=await page.evaluate(()=>({
        page:document.documentElement.scrollWidth,width:innerWidth
      }));
      if(wrap.page>wrap.width+3)throw Error(name+" horizontal scroll "+JSON.stringify(wrap));
      if(await page.locator("h1").count()!==1)throw Error(name+" book lacks single H1");
      const cover=page.locator("#atlasBook");
      if((await cover.getAttribute("data-open"))!=="false")throw Error(name+" cover not closed initially");
      await page.locator("#openBook").click();
      if((await cover.getAttribute("data-open"))!=="true")throw Error(name+" click failed to open cover");
      await page.screenshot({path:output+"/"+name+"-atlas-first-spread.jpg",type:"jpeg",quality:82,fullPage:false});
      await page.locator("#mapOpen").click();
      if(!(await page.locator("#mapDialog").evaluate(d=>d.open)))throw Error(name+" map dialog did not open");
      await page.locator('#mapDialog button[data-city="florence"]').click();
      if(!(await page.locator("#cityHeading").textContent()).includes("Флоренция"))throw Error(name+" city selection failed");
      if(await page.locator("#chapterList button").count()!==3)throw Error(name+" missing three Florence chapters");
      await page.locator('#chapterList button[data-chapter="1"]').click();
      if(await page.locator("#reading").isHidden())throw Error(name+" chapter not visible");
      if(!(await page.locator("#reading-title").textContent()).includes("офортом"))throw Error(name+" wrong Florence chapter");
      await page.waitForFunction(()=>{
        const x=document.getElementById("chapterImage");
        return x.complete&&x.naturalWidth>100;
      },null,{timeout:15000});
      const source=await page.locator("#chapterSource").getAttribute("href");
      if(!source.includes("artic.edu"))throw Error(name+" wrong primary source: "+source);
      await page.locator("#zoomPicture").click();
      if(!(await page.locator("#imageDialog").evaluate(d=>d.open)))throw Error(name+" zoom modal failed");
      await page.locator("#zoomSlider").evaluate(input=>{input.value="150";input.dispatchEvent(new Event("input",{bubbles:true}));});
      if((await page.locator("#zoomLabel").textContent())!=="150%")throw Error(name+" zoom control inactive");
      await page.locator("#imageClose").click();
      await page.locator("#topicsToggle").click();
      if(await page.locator("#topicsPanel").isHidden())throw Error(name+" bookshelf topics did not open");
      await page.locator("#topicsClose").click();
      if(!(await page.locator("#topicsPanel").isHidden()))throw Error(name+" bookshelf topics did not close");
      await page.locator('#topicsToggle').scrollIntoViewIfNeeded();
      await page.locator('.spine[data-city="naples"]').click();
      if(!(await page.locator("#cityHeading").textContent()).includes("Неаполь"))throw Error(name+" Naples book missing");
      await page.locator("#startStory").click();
      const src=await page.locator("#chapterImage").getAttribute("src");
      if(!src.includes("naples_santalucia"))throw Error(name+" Naples historical artifact missing");
      await page.waitForFunction(()=>{
        const x=document.getElementById("chapterImage");
        return x.complete&&x.naturalWidth>100;
      },null,{timeout:15000});
      await page.locator("#quietToggle").click();
      if((await page.locator("#quietToggle").getAttribute("aria-pressed"))!=="true")throw Error(name+" quiet mode not enabled");
      if(!(await page.locator("body").evaluate(x=>x.classList.contains("quiet-mode"))))throw Error(name+" quiet class absent");
      if(errors.length)throw Error(name+" JS errors "+JSON.stringify(errors));
      await page.screenshot({path:output+"/"+name+"-book-open.jpg",type:"jpeg",quality:82,fullPage:false});
      await page.goto(url,{waitUntil:"domcontentloaded"});
      if((await page.locator("#quietToggle").getAttribute("aria-pressed"))!=="true")throw Error(name+" quiet preference did not persist");
      await page.locator("#quietToggle").click();
      await page.reload({waitUntil:"domcontentloaded"});
      if((await page.locator("#atlasBook").getAttribute("data-open"))!=="false")throw Error(name+" cover state not restored");
      await page.screenshot({path:output+"/"+name+"-book-cover.jpg",type:"jpeg",quality:82,fullPage:false});
      console.log("PASS "+name+": cover, map, Florence, Naples, 3 chapters, zoom, topics, quiet mode, local assets");
      await context.close();
    }
    const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:"reduce"});
    const page=await context.newPage();
    await page.goto(new URL("experience/",base).href,{waitUntil:"domcontentloaded"});
    if((await page.locator("#atlasBook").getAttribute("data-open"))!=="true")throw Error("Reduced-motion mode did not open a still book");
    await context.close();
    console.log("PASS reduced motion: no forced cover animation");
  }finally{await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1;});
