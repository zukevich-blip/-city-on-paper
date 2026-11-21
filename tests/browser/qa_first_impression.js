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
      assert.equal(await page.locator("h1").count(),1,"One h1");
      assert.equal(await page.locator(".lh-welcome").count(),1,"Welcome cartouche explains what this is");
      const welcome=await page.locator(".lh-welcome").innerText();
      assert(/Бенуа/.test(welcome)&&/литограф/i.test(welcome),"Welcome names the theme: Benoist and lithographs");
      assert.equal(await page.locator(".lh-steps li").count(),3,"Three-step way to use the site");
      const plaques=await page.locator(".lh-plaque").evaluateAll(a=>a.map(x=>x.getAttribute("href")));
      for(const h of ["book/","poc/compare/?journey=1","eras/","book/#/benoist"])
        assert(plaques.includes(h),"Desk plaque missing: "+h);
      assert.equal(await page.locator(".lh-plaque").count(),4,"Exactly four doors on the desk");
      assert.equal(await page.locator(".lh-row a").count(),3,"Three other masters");
      // hero: real Benoist print and modern photo, slider fades one into the other
      await page.locator("#lhNow").scrollIntoViewIfNeeded();
      await page.evaluate(async()=>{await Promise.all([...document.querySelectorAll(".lh-stage img")].map(async i=>{try{await i.decode();}catch{}}));});
      assert(await page.locator(".lh-stage img").evaluateAll(a=>a.length===2&&a.every(i=>i.naturalWidth>500&&i.naturalHeight>400)),"Print and photo both load");
      assert.equal(await page.locator("#lhNow").evaluate(e=>getComputedStyle(e).opacity),"0","Starts on the print");
      await page.locator("#lhRange").fill("100");
      assert.equal(await page.locator("#lhNow").evaluate(e=>getComputedStyle(e).opacity),"1","Slider reveals the photo");
      const credit=await page.locator("#lhNote").innerText();
      assert(/CC0/.test(credit)&&/CC BY-SA/.test(credit)&&/без подгонки/i.test(credit),"Credits and honest no-fit note");
      assert((await page.locator(".lh-cta .btn").first().getAttribute("href")).includes("madeleine-benoist-carnavalet"),"CTA opens the real compare tool");
      assert(!/↗(?!\ufe0e)/.test(await page.content()),"No bare arrow glyphs that iOS draws as blue emoji");
      const overflow=await page.evaluate(()=>({html:document.documentElement.scrollWidth,viewport:window.innerWidth}));
      assert(overflow.html<=overflow.viewport+5,"No horizontal overflow on "+width+": "+JSON.stringify(overflow));
      const small=await page.locator(".lh-cta .btn,.lh-plaque,.lh-more summary,.navlinks a").evaluateAll(a=>a.filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height<40;}).length);
      assert.equal(small,0,"Touch targets are at least 40 px tall");
      await page.evaluate(()=>window.scrollTo(0,0));
      await page.screenshot({path:path.join(out,"three-second-hero-"+width+".png"),fullPage:false,timeout:25000});
      assert.equal(errors.length,0,"No JS errors: "+errors.join(" | "));
      console.log("PASS first impression "+width+"px: welcome, four doors, Benoist then/now slider, no overflow");
      await context.close();
    }
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});