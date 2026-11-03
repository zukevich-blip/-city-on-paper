// Smoke-test two newly integrated museum rooms without relying on external archives.
const { chromium }=require("playwright");
const fs=require("fs");
const [,,origin,outDir]=process.argv;
if(!origin||!outDir)throw Error("Usage: qa_museum_rooms.js <origin> <outDir>");
fs.mkdirSync(outDir,{recursive:true});
const checks=[];
function verify(name,condition){checks.push({name,pass:!!condition});console.log((condition?"PASS ":"FAIL ")+name);}
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    for(const view of [{n:"iphone-390",w:390,h:844},{n:"ipad-820",w:820,h:1180},{n:"desktop-1440",w:1440,h:900}]){
      const context=await browser.newContext({viewport:{width:view.w,height:view.h},acceptDownloads:true});
      const page=await context.newPage(),errors=[];page.on("pageerror",e=>errors.push(e.message));
      await page.goto(new URL("ornaments/",origin).href,{waitUntil:"domcontentloaded"});
      await page.waitForFunction(()=>document.querySelectorAll("#records .item").length===14,{timeout:25000});
      verify(view.n+" 14 ornament objects",await page.locator("#records .item").count()===14);
      verify(view.n+" no horizontal scroll",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      verify(view.n+" originals link to archive",await page.locator("#records .item a").first().getAttribute("href").then(x=>x.startsWith("https://archive.org/")));
      await page.locator("#catalogue").selectOption("bakewell1887");
      verify(view.n+" first historical catalog filters eight items",await page.locator("#records .item").count()===8);
      await page.locator("#catalogue").selectOption("all");
      await page.locator("#search").fill("капители");
      verify(view.n+" searchable item",await page.locator("#records .item").count()===1);
      await page.locator("#search").fill("");
      await page.screenshot({path:outDir+"/"+view.n+"-ornaments.jpg",type:"jpeg",quality:70,fullPage:true});
      await page.goto(new URL("atelier/bargue/",origin).href,{waitUntil:"domcontentloaded"});
      verify(view.n+" drawing canvas present",await page.locator("canvas#drawing").count()===1);
      verify(view.n+" five learning steps",await page.locator("[data-step]").count()===5);
      verify(view.n+" no canvas page overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      const box=await page.locator("#drawing").boundingBox();
      if(box){
        await page.mouse.move(box.x+box.width*.3,box.y+box.height*.25);
        await page.mouse.down();
        await page.mouse.move(box.x+box.width*.55,box.y+box.height*.45,{steps:5});
        await page.mouse.up();
      }
      verify(view.n+" stroke recorded",await page.locator("#stroke-count").innerText().then(x=>x.includes("1 линия")));
      await page.reload({waitUntil:"domcontentloaded"});
      verify(view.n+" stroke preserved",await page.locator("#stroke-count").innerText().then(x=>x.includes("1 линия")));
      await page.locator("#undo").click();
      verify(view.n+" undo works",await page.locator("#stroke-count").innerText().then(x=>x.includes("0 линий")));
      verify(view.n+" no JS errors",errors.length===0);
      await page.screenshot({path:outDir+"/"+view.n+"-drawing.jpg",type:"jpeg",quality:70,fullPage:true});
      await context.close();
    }
    const page=await browser.newPage();
    await page.goto(origin,{waitUntil:"domcontentloaded"});
    verify("home links to two new integrated rooms",
      await page.locator('a[href="ornaments/"]').count()>0&&
      await page.locator('a[href="atelier/bargue/"]').count()>0);
  }finally{await browser.close();}
  fs.writeFileSync(outDir+"/qa_museum_rooms.json",JSON.stringify(checks,null,2));
  console.log(checks.length+" checks, "+checks.filter(x=>!x.pass).length+" failures");
  if(checks.some(x=>!x.pass))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
