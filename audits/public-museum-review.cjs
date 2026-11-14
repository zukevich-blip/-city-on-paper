"use strict";
/* Read-only external audit of the published museum. No paid API or mutation. */
const fs=require("node:fs");
const path=require("node:path");
const {chromium,webkit}=require("playwright");
const AxeBuilder=require("@axe-core/playwright").default;
const BASE="https://zukevich-blip.github.io/-city-on-paper/";
const OUT="review-results";
const ROUTES=[
  {id:"home",uri:"",wait:"body"},
  {id:"paris",uri:"eras/#/city/paris",wait:"#cPlaceSelect"},
  {id:"cities",uri:"cities/",wait:"body"},
  {id:"salon",uri:"salon/",wait:"body"},
  {id:"compare",uri:"poc/compare/",wait:"body"},
];
const report={date:new Date().toISOString(),base:BASE,method:"free Chromium + axe-core + WebKit smoke",
  public_revision:null,checks:[],internal_links:[],errors:[],summary:{}};
const dest=file=>path.join(OUT,file);
fs.mkdirSync(OUT,{recursive:true});
async function check(browser,engine,width,item){
  const ctx=await browser.newContext({viewport:{width,height:840},isMobile:width===390,hasTouch:width===390});
  const page=await ctx.newPage();
  const test={engine,width,route:item.id,uri:item.uri,errors:[],violations:[],status:null,horizontalOverflow:false,
    brokenVisibleImages:[],experience:{},internal_links:[]};
  page.on("pageerror",err=>test.errors.push("JS: "+err.message.slice(0,280)));
  const url=BASE+item.uri;
  try{
    const response=await page.goto(url,{waitUntil:"domcontentloaded",timeout:45000});
    test.status=response?.status()||0;
    if(test.status!==200)throw Error("HTTP "+test.status+" on "+url);
    await page.locator(item.wait).first().waitFor({timeout:30000});
    const frame=async(stage,element)=>{
      if(engine!=="chromium")return;
      try{
        if(element)await page.locator(element).first().scrollIntoViewIfNeeded({timeout:15000});
        await page.screenshot({path:dest(item.id+"-"+width+"-"+stage+".png"),fullPage:false,timeout:30000});
      }catch(e){test.errors.push("Screenshot "+stage+": "+String(e.message||e).slice(0,200));}
    };
    if(item.id==="home"){
      await page.locator(".museum-wow").waitFor({timeout:20000});
      test.experience.heroFeatures=await page.locator(".wow-features>a").count();
      test.experience.pairImages=await page.locator(".wow-duet img").count();
      if(test.experience.heroFeatures!==4)test.errors.push("Homepage lost four first-impression feature doors");
      if(test.experience.pairImages!==2)test.errors.push("Homepage lost actual historical/current image pair");
      await page.locator(".wow-duet img").evaluateAll(async images=>{
        await Promise.all(images.map(x=>x.decode().catch(()=>{})));
      });
      test.experience.pairImagesLoaded=await page.locator(".wow-duet img").evaluateAll(
        images=>images.length===2&&images.every(x=>x.naturalWidth>500&&x.naturalHeight>400));
      if(!test.experience.pairImagesLoaded)test.errors.push("Live first-impression image pair did not load");
      test.experience.directComparison=await page.locator(".wow-primary").getAttribute("href");
      if(!test.experience.directComparison?.includes("poc/compare/"))
        test.errors.push("Main CTA no longer opens the actual comparison");
      await frame("09-first-impression",".museum-wow");
    }
    if(item.id==="paris"){
      await frame("01-landmarks","#cPlaceSelect");
      const historic=page.locator('#cPlaceSelect option[data-on-plan="true"]').first();
      if(await historic.count()){
        const key=await historic.getAttribute("value");
        await page.locator("#cPlaceSelect").selectOption(key);
        await page.locator("#cPlaceNow").click();
        await frame("02-current-map","#cnow");
        if(await page.locator("#cNew").getAttribute("aria-selected")!=="true")
          test.errors.push("Historic landmark did not navigate to modern map");
        await page.locator("#cPlaceOld").click();
        await frame("03-historic-plan","#cplan");
        if(await page.locator("#cOld").getAttribute("aria-selected")!=="true")
          test.errors.push("Modern landmark did not navigate back to old map");
        test.experience.mapSwitch=true;
      }else test.errors.push("No historical site with map coordinates");
      await page.locator("#vpaCompare").waitFor({timeout:30000});
      test.experience.artworkHistory=await page.locator("#vpaStory .art-history").count()===1;
      if(!test.experience.artworkHistory)test.errors.push("The selected print has no individual history");
      test.experience.viewpointAtlas=true;
      if(!(await page.locator("#vpaSelected").textContent())?.trim())
        test.errors.push("No historical work selected");
      await frame("04-viewpoint","#vpaCompare");
      if(await page.locator("#vpaWipe").isEnabled()){
        await page.locator("#vpaWipe").click();
        await frame("05-wipe","#vpaCompare");
        test.experience.wipe=await page.locator("#vpaCompare").evaluate(e=>e.classList.contains("is-wipe"));
        if(!test.experience.wipe)test.errors.push("Wipe comparison failed");
        test.experience.visibleCredits=await page.locator("#vpaWipeCredits").isVisible()&&
          await page.locator("#vpaWipeCredits > div").count()===2;
        if(!test.experience.visibleCredits)test.errors.push("Wipe mode is missing both independently readable image credits");
        await page.locator("#vpaSide").click();
        await frame("06-side-by-side","#vpaCompare");
      }
      test.experience.cameraUncertainty=(await page.locator("#vpaCompareTruth").textContent())?.includes("подтверждено")||false;
      if(!test.experience.cameraUncertainty)test.errors.push("Missing uncertainty disclaimer");
    }
    if(item.id==="salon"){
      await page.locator("#gallery .art").first().waitFor({timeout:30000});
      const n=await page.locator("#gallery .art").count(),withHistory=await page.locator("#gallery .art-history").count();
      test.experience.artworks=n;test.experience.stories=withHistory;
      if(n<5 || n!==withHistory)test.errors.push("Individual sourced stories missing in the Salon: "+withHistory+"/"+n);
      else{
        await page.locator("#gallery .art-history summary").first().click();
        test.experience.storyOpened=await page.locator("#gallery .art-history-body").first().isVisible();
        test.experience.sourced=await page.locator("#gallery .art-history-sources a").first().count()>0;
        if(!test.experience.storyOpened||!test.experience.sourced)
          test.errors.push("Artwork story is not expandable or has no museum source");
        await frame("08-individual-history","#gallery .art-history-body");
      }
    }
    test.horizontalOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+5);
    if(test.horizontalOverflow){
      test.overflowElements=await page.evaluate(()=>Array.from(document.querySelectorAll("body *"))
        .filter(el=>{
          const rect=el.getBoundingClientRect(),style=getComputedStyle(el);
          return rect.width>0&&rect.right>innerWidth+5&&rect.left<innerWidth&&
            style.display!=="none"&&style.visibility!=="hidden"&&!el.closest("[hidden]");
        })
        .sort((a,b)=>b.getBoundingClientRect().right-a.getBoundingClientRect().right)
        .slice(0,16)
        .map(el=>({tag:el.tagName.toLowerCase(),id:el.id||null,
          className:typeof el.className==="string"?el.className.slice(0,140):"",
          right:Math.round(el.getBoundingClientRect().right),width:Math.round(el.getBoundingClientRect().width)})));
    }
    if(test.horizontalOverflow)test.overflowDetail=await page.evaluate(()=>({
      scrollWidth:document.documentElement.scrollWidth,viewport:innerWidth,
      suspects:[...document.querySelectorAll("body *")]
        .map(el=>({el,r:el.getBoundingClientRect()}))
        .filter(x=>x.r.width>0&&x.r.right>innerWidth+5&&x.r.left<innerWidth+200)
        .sort((a,b)=>b.r.right-a.r.right)
        .slice(0,8).map(x=>({tag:x.el.tagName,css:x.el.className?.toString().slice(0,90),
          id:x.el.id,right:Math.round(x.r.right),width:Math.round(x.r.width)}))
    }));
    test.brokenVisibleImages=await page.locator("img").evaluateAll(images=>images
      .filter(i=>{const r=i.getBoundingClientRect();return r.width>0&&r.height>0&&r.top<innerHeight&&r.bottom>0&&i.complete&&i.naturalWidth===0;})
      .slice(0,12).map(i=>i.currentSrc||i.src||"unknown"));
    if(test.brokenVisibleImages.length)test.errors.push(test.brokenVisibleImages.length+" visible broken images");
    if(engine==="chromium"){
      try{
        const axe=await new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa"]).analyze();
        test.violations=axe.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,helpUrl:v.helpUrl,
          affected:v.nodes.length,selectors:v.nodes.slice(0,3).map(n=>n.target.join(" "))}));
      }catch(e){test.errors.push("axe scan: "+String(e.message||e).slice(0,260));}
    }
    if(["cities","salon","compare"].includes(item.id)&&engine==="chromium")await frame("07-gallery","body");
    if((item.id==="home"||item.id==="paris")&&engine==="chromium"){
      await page.screenshot({path:dest(item.id+"-"+width+".png"),fullPage:false,timeout:30000});
    }
    if(engine==="chromium"&&width===1440){
      test.internal_links=await page.locator("a[href]").evaluateAll(links=>[...new Set(links
        .map(a=>a.href).filter(u=>u.startsWith("https://zukevich-blip.github.io/-city-on-paper/"))
        .map(u=>u.split("#")[0].split("?")[0]))].slice(0,110));
    }
  }catch(e){test.errors.push("Audit failure: "+String(e.message||e).slice(0,500));}
  await ctx.close();
  return test;
}
async function verifyInternalLinks(links){
  const all=[...new Set(links)].slice(0,120);
  let next=0;
  async function worker(){
    while(next<all.length){
      const url=all[next++];
      try{
        const response=await fetch(url,{method:"HEAD",signal:AbortSignal.timeout(18000),
          headers:{"User-Agent":"CityOnPaper-FreeQA/1.0"}});
        report.internal_links.push({url,status:response.status,ok:response.ok});
      }catch(e){report.internal_links.push({url,status:null,ok:false,error:String(e).slice(0,150)});}
    }
  }
  await Promise.all(Array.from({length:4},worker));
}
async function run(){
  const engines=[
    {name:"chromium",factory:chromium,targets:ROUTES,widths:[390,1440]},
    {name:"webkit",factory:webkit,targets:ROUTES.filter(x=>["home","paris"].includes(x.id)),widths:[390]}
  ];
  for(const config of engines){
    let browser;
    try{
      browser=await config.factory.launch({headless:true,args:config.name==="chromium"?["--no-sandbox"]:[]});
      for(const width of config.widths)for(const route of config.targets){
        const res=await check(browser,config.name,width,route);
        report.checks.push(res);
        console.log("AUDIT",config.name,width,route.id,"HTTP",res.status,
          "errors",res.errors.length,"WCAG violations",res.violations.length);
      }
    }catch(e){report.errors.push(config.name+" engine: "+String(e.message||e));}
    finally{if(browser)await browser.close();}
  }
  try{
    const response=await fetch(BASE+"PUBLIC_DEMO_REVISION.json",{signal:AbortSignal.timeout(20000)});
    const data=await response.json();
    report.public_revision={sha:data.source_revision,qa_run:data.qa_run,qa_conclusion:data.qa_conclusion,
      scientific_acceptance:data.scientific_acceptance};
  }catch(e){report.errors.push("Published revision unavailable: "+String(e));}
  await verifyInternalLinks(report.checks.flatMap(x=>x.internal_links||[]));
  report.summary={
    checkedPages:report.checks.length,
    hardErrors:report.checks.reduce((a,b)=>a+b.errors.length,0)+report.errors.length,
    criticalWCAG:report.checks.flatMap(x=>x.violations).filter(v=>v.impact==="critical").length,
    seriousWCAG:report.checks.flatMap(x=>x.violations).filter(v=>v.impact==="serious").length,
    brokenInternalLinks:report.internal_links.filter(x=>!x.ok).length,
    horizontalOverflows:report.checks.filter(x=>x.horizontalOverflow).length
  };
  fs.writeFileSync(dest("museum-review.json"),JSON.stringify(report,null,2));
  const t=report.summary;
  const summary=[
    "## Бесплатный независимый аудит City on Paper",
    "Дата UTC: "+report.date,
    "Опубликованная ревизия: "+(report.public_revision?.sha||"не установлена"),
    "Проверено страниц/устройств: "+t.checkedPages,
    "Сбои сценариев и JS: "+t.hardErrors,
    "WCAG: critical "+t.criticalWCAG+", serious "+t.seriousWCAG+" (число правил, не отдельных узлов)",
    "Сломанные внутренние ссылки: "+t.brokenInternalLinks+"/"+report.internal_links.length,
    "Горизонтальные переполнения: "+t.horizontalOverflows,
    "Элементы справа за экраном: "+JSON.stringify(report.checks.filter(x=>x.horizontalOverflow).map(x=>({engine:x.engine,width:x.width,route:x.route,elements:x.overflowElements?.slice(0,5)}))),
    "",
    "Ревизор не меняет код и не публикует фотографии. Замечания WCAG требуют ручной оценки.",
    "Подробности: museum-review.json и снимки экрана в артефактах запуска."
  ];
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,summary.join("\n")+"\n");
  console.log(summary.join("\n"));
  if(t.hardErrors||t.brokenInternalLinks)process.exitCode=1;
}
run().catch(e=>{console.error(e);process.exitCode=1;});
