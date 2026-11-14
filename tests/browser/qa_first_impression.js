/* The homepage has 3 seconds to show a real feature, not an archive introduction. */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const { chromium }=require("playwright");
const base=(process.argv[2]||"http://127.0.0.1:8765/").replace(/\/?$/,"/");
const out=process.argv[3]||"/tmp/city-on-paper-screens";
(async()=>{
  fs.mkdirSync(out,{recursive:true});
  const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
  try{
    for(const width of [320,390,820,1440]){
      const context=await browser.newContext({viewport:{width,height:900},reducedMotion:"reduce"});
      const page=await context.newPage(),errors=[];
      page.on("pageerror",e=>errors.push(e.message));
      const response=await page.goto(base,{waitUntil:"domcontentloaded",timeout:30000});
      assert.equal(response?.status(),200,"Museum homepage responds HTTP 200");
      assert.equal(await page.locator(".museum-frontdoor").count(),1);
      assert.equal(await page.locator(".wow-features>a").count(),4,"Four ways to explore visible in one section");
      assert(await page.locator(".wow-primary").isVisible(),"Primary direct demo CTA is visible");
      assert(await page.locator(".wow-secondary").isVisible(),"Second atlas CTA visible");
      assert(await page.locator("#frontQuery").count()===1,"Preserve city search");
      const labels=await page.locator(".wow-features strong").allTextContents();
      for(const word of ["эпохи","картам","художника","истории"]){
        assert(labels.some(t=>t.toLowerCase().includes(word)),word+" feature is missing");
      }
      const images=page.locator(".wow-duet img");
      assert.equal(await images.count(),2,"Real pair is prominently presented");
      await page.evaluate(async()=>{
        await Promise.all([...document.querySelectorAll(".wow-duet img")].map(async i=>{
          try{await i.decode();}catch{}
        }));
      });
      assert(await images.evaluateAll(a=>a.every(i=>i.naturalWidth>500&&i.naturalHeight>400)),
        "Both original artwork and modern documentary photo actually load");
      assert(await page.locator(".wow-visual-bottom").innerText().then(s=>s.includes("разные точки наблюдения")),
        "No false viewpoint match on the first screen");
      assert(await page.locator(".wow-visual-bottom").innerText().then(s=>s.includes("CC BY-SA")),
        "Modern photograph attribution is present");
      assert((await page.locator(".wow-primary").getAttribute("href")).includes("poc/compare/"),
        "Hero points to real interactive compare");
      assert((await page.locator(".wow-secondary").getAttribute("href")).includes("eras/"),
        "Hero points to real historical atlas");
      const overflow=await page.evaluate(()=>({
        body:document.body.scrollWidth,
        html:document.documentElement.scrollWidth,
        viewport:window.innerWidth
      }));
      assert(overflow.html<=overflow.viewport+5,
        "No horizontal overflow on "+width+": "+JSON.stringify(overflow));
      const clip=await page.locator(".museum-frontdoor").evaluate(e=>{
        const r=e.getBoundingClientRect();return {top:r.top,width:r.width,right:r.right};
      });
      assert(clip.top<320,"Actual product showcase appears within the first screen, not below long introduction");
      await page.screenshot({path:path.join(out,"three-second-hero-"+width+".png"),fullPage:false,timeout:25000});
      assert.equal(errors.length,0,"No JS errors: "+errors.join(" | "));
      console.log("PASS first impression "+width+"px: actual historical photo pair, two actions, four features, no overflow");
      await context.close();
    }
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});