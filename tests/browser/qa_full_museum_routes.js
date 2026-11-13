/* Comprehensive cross-hall internal-link, mobile UX and image audit. */
"use strict";
(async function auditMuseumJourneys() {
  const {chromium}=require("playwright"), fs=require("node:fs"), path=require("node:path");
  const origin=process.argv[2]||"http://127.0.0.1:8791/";
  const output=process.argv[3]||"/tmp/museum-route-audit.json";
  const routes=["","walk/","stories/","stories/paris-on-paper/","atlas/","experience/","eras/","salon/","closeup/","exhibitions/city-as-evidence/","exhibitions/lost-florence/","photography/","journeys/","cities/","world/","poc/compare/","poc/compare/editor.html","atlas-prototype/","discover/","detective/","fieldwork/","submit/","studio/","printlab/","atelier/bargue/","atelier/ornament/","ornaments/","ideas/","desk/","exhibitions/lost-florence/","eras/#/epochs","eras/#/city/paris","eras/#/city/florence","eras/#/city/naples"];
  const browser=await chromium.launch({headless:true});
  const base=new URL(origin), results=[],internal=new Map(),external=new Set();
  for (const width of [390,1440]) {
    const context=await browser.newContext({viewport:{width,height:850},isMobile:width===390,hasTouch:width===390,ignoreHTTPSErrors:false});
    for(const route of routes) {
      const page=await context.newPage(),jserrors=[],badHTTP=[];
      page.on("pageerror", e=>jserrors.push(e.message.slice(0,180)));
      page.on("response",r=>{if(r.status()>=400 && r.url().startsWith(base.origin)){badHTTP.push({status:r.status(),url:r.url()})}});
      const url=new URL(route,base).href; let status=0,navError="";
      try {const res=await page.goto(url,{waitUntil:"domcontentloaded",timeout:7000});status=res?.status()||0;await page.waitForTimeout(250);}
      catch(e){navError=String(e.message).slice(0,180);}
      const details=await page.evaluate(()=>{
        const anchors=[...document.querySelectorAll("a[href]")].map(a=>({href:a.href,label:(a.innerText||a.getAttribute("aria-label")||"").trim().slice(0,50)}));
        const imgs=[...document.images].filter(i=>{const box=i.getBoundingClientRect();return box.width>10&&box.height>10&&box.bottom>-100&&box.top<innerHeight+500});
        return {title:document.title,chars:(document.body?.innerText||"").length,
          scrollWidth:document.documentElement.scrollWidth,width:innerWidth,
          anchors,
          brokenVisibleImages:imgs.filter(i=>i.getAttribute("src") && i.currentSrc && i.complete && i.naturalWidth===0).map(i=>i.currentSrc.slice(0,180)).slice(0,12),
          hasMain:!!document.querySelector("main"),hasH1:!!document.querySelector("h1"),
          buttonNames:[...document.querySelectorAll("button")].filter(x=>!x.getAttribute("aria-label")&&!x.innerText.trim()&&!x.getAttribute("title")).length,
          pending:/Загружаем атлас…/.test(document.body?.innerText||"") && !document.querySelector(".view"),
          menu:!!document.querySelector("#museumBar"),formImages:document.querySelectorAll('input[type="file"]').length
        };
      }).catch(e=>({error:String(e)}));
      const errors=[...new Set(jserrors)].slice(0,7);
      for(const a of details.anchors||[]){
        try{const u=new URL(a.href);
          if(u.origin===base.origin && u.pathname.startsWith(base.pathname)){
            const rel=u.pathname.slice(base.pathname.length);
            if(!internal.has(rel))internal.set(rel,[]);
            const callers=internal.get(rel);if(callers.length<4)callers.push({from:route,label:a.label,hash:u.hash});
          }else if(/^https?:$/.test(u.protocol))external.add(u.origin);
        }catch{}
      }
      results.push({width,route,status,navError,...details,anchors:undefined,jsErrors:errors,badHTTP:badHTTP.slice(0,6)});
      await page.close();
    }
    await context.close();
  }
  const probe=await browser.newContext({ignoreHTTPSErrors:false});
  const list=[...internal.entries()],checked=new Array(list.length),workers=Math.min(14,list.length);
  let index=0;
  await Promise.all(Array.from({length:workers},async()=>{
    while(index<list.length){
      const n=index++, [rel,referrers]=list[n],target=new URL(rel,base).href;
      let status=null;
      try {const response=await probe.request.head(target,{timeout:3500,maxRedirects:3});status=response.status();}
      catch(e){status="NETWORK_ERROR";}
      checked[n]={path:rel,status,referrers};
    }
  }));
  await probe.close();await browser.close();
  const broken=checked.filter(x=>typeof x.status!=="number"||x.status>=400);
  // The public release builder creates these four policy pages. They are deliberately
  // absent in the source checkout and must be validated in delivered-package QA.
  const generated=new Set(["about/","rights/","privacy/","contribute/"]);
  const sourceOnlyGenerated=broken.filter(x=>generated.has(x.path) && x.status===404);
  const realBroken=broken.filter(x=>!sourceOnlyGenerated.includes(x));
  const overflows=results.filter(x=>x.scrollWidth>x.width+8);
  const exceptions=results.filter(x=>x.jsErrors?.length||x.navError||x.status>=400);
  const images=results.filter(x=>x.brokenVisibleImages?.length);
  const report={origin,scanned_routes:results.length,unique_internal_targets:checked.length,unique_external_hosts:external.size,broken_internal:realBroken,generated_policy_pages_to_validate_in_package:sourceOnlyGenerated,overflows,exceptions,broken_images:images,all_pages:results.map(({route,width,title,chars,status,menu,hasMain,hasH1,buttonNames,pending})=>({route,width,title,chars,status,menu,hasMain,hasH1,buttonNames,pending}))};
  fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2));
  console.log("SITE-AUDIT-SUMMARY",JSON.stringify({routes:results.length,internal:checked.length,externals:external.size,broken:realBroken.length,generated_pages:sourceOnlyGenerated.length,overflows:overflows.length,exceptions:exceptions.length,brokenImages:images.length}));
  console.log("SITE-AUDIT-BROKEN-LINKS",JSON.stringify(realBroken.slice(0,35)));
  console.log("SITE-AUDIT-OVERFLOWS",JSON.stringify(overflows.map(x=>({r:x.route,w:x.width,scroll:x.scrollWidth})).slice(0,15)));
  console.log("SITE-AUDIT-JS-ERRORS",JSON.stringify(exceptions.map(x=>({r:x.route,w:x.width,errors:x.jsErrors?.slice(0,3),http:x.badHTTP?.slice(0,2)})).slice(0,18)));
  console.log("SITE-AUDIT-IMAGES",JSON.stringify(images.map(x=>({r:x.route,w:x.width,img:x.brokenVisibleImages.slice(0,2)})).slice(0,15)));
  if(realBroken.length)process.exitCode=2;
})().catch(e=>{console.error(e);process.exitCode=1});
