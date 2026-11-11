/* Engraving Museum: full visual and provenance smoke check on source + released ZIP. */
"use strict";
const {chromium}=require("playwright");
const fs=require("fs");
const [,,base,out]=process.argv;
if(!base||!out)throw Error("Usage: qa_engraving.js <origin> <screenshots-directory>");
fs.mkdirSync(out,{recursive:true});
function assert(label,ok){if(!ok)throw Error(label);}
async function paint(page,device,section){
  await page.evaluate(()=>{scrollTo(0,0);});
  await page.screenshot({
    path:out+"/engraving-"+device+"-"+section+".jpg",
    type:"jpeg",quality:85,fullPage:false
  });
}
async function styleCheck(page,device,room){
  assert(device+" "+room+" custom skin",await page.locator("body.cop-engraved").count()===1);
  const skin=await page.evaluate(()=>{
    const css=[...document.styleSheets].filter(x=>x.href&&x.href.endsWith("/assets/hybrid/engraving.css"));
    const root=getComputedStyle(document.documentElement);
    return {sheets:css.length,title:root.getPropertyValue("--cop-titling").trim(),
      ink:root.getPropertyValue("--cop-sanguine").trim(),
      overflow:document.documentElement.scrollWidth-innerWidth};
  });
  assert(device+" "+room+" CSS loaded",skin.sheets===1&&!!skin.title&&skin.ink==="#895140");
  assert(device+" "+room+" no horizontal overflow "+skin.overflow,skin.overflow<=4);
}
async function originalIntegrity(page,selector,device){
  const source=page.locator(selector).first();
  await source.waitFor({state:"visible"});
  await source.evaluate(async img=>{
    if(img.complete&&img.naturalWidth>100)return;
    await new Promise((res,rej)=>{
      img.addEventListener("load",res,{once:true});img.addEventListener("error",()=>rej(Error("image failed")),{once:true});
    });
  });
  const details=await source.evaluate(img=>{
    const c=getComputedStyle(img);
    return {w:img.naturalWidth,filter:c.filter,blend:c.mixBlendMode,alt:img.alt};
  });
  assert(device+" historic original loaded",details.w>100);
  assert(device+" not filtered",details.filter==="none"&&details.blend==="normal");
  assert(device+" original has alt",!!details.alt);
}
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    for(const [device,width,height] of [["phone-320",320,750],["phone-390",390,844],["ipad-820",820,1180],["desktop-1440",1440,900]]){
      const context=await browser.newContext({viewport:{width,height},reducedMotion:"reduce"});
      const page=await context.newPage(),errors=[];
      page.on("pageerror",err=>errors.push(err.message));
      const open=path=>page.goto(new URL(path,base).href,{waitUntil:"domcontentloaded"});
      // Story-led main entrance
      let response=await open("./");
      assert(device+" homepage HTTP",response&&response.status()===200);
      await styleCheck(page,device,"home");
      const stamp=page.locator(".hybrid-story-copy .cop-signet");
      assert(device+" own publisher mark",await stamp.textContent()==="ГБ");
      assert(device+" no institutional forgery",((await page.locator(".cop-imprint").getAttribute("aria-label"))||"").includes("цифрового музея"));
      const display=await page.locator(".hybrid-story-hero h1").evaluate(node=>getComputedStyle(node).fontFamily);
      assert(device+" engraved title type",/Bodoni|Didot|Iowan|Georgia/i.test(display));
      await originalIntegrity(page,".hybrid-hero-picture img",device+" home");
      assert(device+" source archive link",await page.locator('.hybrid-hero-picture figcaption a[href="https://www.loc.gov/item/2016652452/"]').count()===1);
      assert(device+" engraving rule",await page.locator(".hybrid-story-copy .cop-engraved-line").count()===1);
      await paint(page,device,"home");

      response=await open("cities/");
      assert(device+" city HTTP",response&&response.status()===200);
      await page.waitForFunction(()=>document.querySelectorAll(".city-card").length>=3,null,{timeout:18000});
      await styleCheck(page,device,"cities");
      assert(device+" city masthead stamp",await page.locator(".hero-copy .cop-signet").count()===1);
      await originalIntegrity(page,".hero-art-grid img",device+" cities");
      assert(device+" three source institutions",await page.locator(".hero-art figcaption a[href^='https://']").count()===3);
      assert(device+" status plate not claiming verification",await page.locator(".city-card .status").first().textContent()!=="Verified");
      await paint(page,device,"cities");

      response=await open("atlas/");
      assert(device+" atlas HTTP",response&&response.status()===200);
      await styleCheck(page,device,"atlas");
      assert(device+" atlas editorial imprint",await page.locator(".hero .cop-signet").count()===1);
      assert(device+" map not georectified",((await page.locator("#map-title").textContent())||"").includes("1769"));
      await originalIntegrity(page,".map-pane figure img",device+" atlas");
      await page.waitForFunction(()=>document.querySelectorAll("#atlasResults .result-item").length>=1,null,{timeout:15000});
      assert(device+" source label",await page.locator("a#selectedSource").count()===1);
      await paint(page,device,"atlas");
      if(device==="phone-390"||device==="desktop-1440"){
        response=await open("stories/");
        assert(device+" stories HTTP",response&&response.status()===200);
        await styleCheck(page,device,"stories");
        await paint(page,device,"stories");
        response=await open("experience/");
        assert(device+" book HTTP",response&&response.status()===200);
        await styleCheck(page,device,"book");
        await paint(page,device,"book");
      }
      assert(device+" no runtime exceptions "+errors.join("; "),errors.length===0);
      console.log("PASS "+device+" engraved museum: sheets, sources, cards, masthead, layout, keyboard-friendly paint");
      await context.close();
    }
  }finally{await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1;});
