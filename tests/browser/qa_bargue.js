// Automated browser checks for Bargue drawing atelier.
// Run: node tests/browser/qa_bargue.js http://127.0.0.1:8765/atelier/bargue/ /tmp/screen
const { chromium } = require("playwright");
const fs = require("fs");
const [,,base,outDir] = process.argv;
if (!base || !outDir) throw Error("base URL and screenshots directory required");
fs.mkdirSync(outDir,{recursive:true});
const cases=[["iphone-375",375,812],["iphone-390",390,844],["ipad-820",820,1180],["desktop-1440",1440,900]];
const results=[];
function check(name,value){results.push([name,!!value]);console.log((value?"PASS ":"FAIL ")+name);}
(async()=>{
const browser=await chromium.launch({headless:true});
for(const [name,width,height] of cases){
  const ctx=await browser.newContext({viewport:{width,height},acceptDownloads:true});
  const page=await ctx.newPage();
  const errors=[];page.on("pageerror",e=>errors.push(String(e)));
  const response=await page.goto(base,{waitUntil:"networkidle"});
  check(name+" HTTP 200",response.status()===200);
  check(name+" Russian language + original drawing",await page.locator("html[lang=ru]").count()===1&&await page.locator("#reference svg").count()===0&&await page.locator("svg#reference").count()===1);
  check(name+" no third-party image requests",(await page.locator("img").count())===0);
  check(name+" no horizontal overflow",await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth+1));
  check(name+" five functional steps",(await page.locator("[data-step]").count())===5);
  await page.locator("[data-step='2']").click();
  check(name+" change step",await page.locator("#stage-title").textContent().then(s=>s.includes("контур")));
  const canvas=page.locator("#drawing"),b=await canvas.boundingBox();
  const start={x:b.x+b.width*.25,y:b.y+b.height*.25},end={x:b.x+b.width*.65,y:b.y+b.height*.64};
  await page.mouse.move(start.x,start.y);await page.mouse.down();await page.mouse.move(end.x,end.y,{steps:12});await page.mouse.up();
  check(name+" one stroke drawn",await page.locator("#stroke-count").textContent().then(s=>s.includes("1 линия")));
  await page.reload({waitUntil:"networkidle"});
  check(name+" drawing retained after reload",await page.locator("#stroke-count").textContent().then(s=>s.includes("1 линия")));
  await page.locator("#undo").click();
  check(name+" undo stroke",await page.locator("#stroke-count").textContent().then(s=>s.includes("0 линий")));
  await page.locator("#guide").uncheck();
  check(name+" guides toggle",await page.locator("#guide").isChecked().then(x=>!x));
  let exported=false;
  try{const [download]=await Promise.all([page.waitForEvent("download",{timeout:5000}),page.locator("#save").click()]);exported=download.suggestedFilename().endsWith(".png");}catch(e){}
  check(name+" PNG export",exported);
  check(name+" no runtime errors",errors.length===0);
  await page.screenshot({path:outDir+"/"+name+"-bargue.jpg",type:"jpeg",quality:65,fullPage:name==="iphone-390"});
  await ctx.close();
}
const home=await browser.newPage();
await home.goto(new URL("../../index.html",base).href,{waitUntil:"networkidle"});
check("museum links to atelier",(await home.locator("a[href='atelier/bargue/index.html']").count())>=1);
await browser.close();
const fails=results.filter(x=>!x[1]);console.log(results.length+" checks, "+fails.length+" failed");
if(fails.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
