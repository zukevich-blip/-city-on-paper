const {chromium}=require("playwright");
const fs=require("fs");
const [,,root,outDir]=process.argv;
if(!root||!outDir)throw Error("Need origin URL + screenshot dir");
fs.mkdirSync(outDir,{recursive:true});
const results=[];
function check(name,ok){const pass=!!ok;console.log((pass?"PASS ":"FAIL ")+name);results.push({name,pass});}
async function run(){
 const browser=await chromium.launch({headless:true});
 try{
 for(const [name,width,height] of [["phone-390",390,844],["tablet-820",820,1180],["desktop-1440",1440,900]]){
  const ctx=await browser.newContext({viewport:{width,height},acceptDownloads:true});
  const page=await ctx.newPage();const errors=[];
  page.on("pageerror",e=>errors.push(e.message));
  const res=await page.goto(new URL("atelier/ornament/",root).href,{waitUntil:"domcontentloaded"});
  check(name+" ornaments status",res.status()===200);
  await page.waitForFunction(()=>document.querySelectorAll("#cards .card").length===14);
  check(name+" all 14 catalog records",await page.locator("#cards .card").count()===14);
  check(name+" no horizontal scroll ornament",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  check(name+" original metadata only",await page.locator("#cards img").count()===0);
  await page.locator("#categoryFilter").selectOption("Capital");
  check(name+" filters capitals",await page.locator("#cards .card").count()===1);
  await page.locator("#reset").click();
  await page.locator("#search").fill("2598");
  check(name+" searches model numbers",await page.locator("#cards .card").count()===1);
  check(name+" official archive link",await page.locator("#cards .card a").first().getAttribute("href").then(s=>s.includes("archive.org")));
  await page.locator("#reset").click();
  check(name+" no ornament JS errors",errors.length===0);
  await page.screenshot({path:outDir+"/"+name+"-ornament.jpg",type:"jpeg",quality:70,fullPage:true});
  await page.goto(new URL("atelier/bargue/",root).href,{waitUntil:"domcontentloaded"});
  check(name+" original SVG art not PDF",await page.locator("svg#reference").count()===1);
  check(name+" five drawing lessons",await page.locator("[data-step]").count()===5);
  check(name+" no horizontal scroll drawing",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.locator('[data-step="2"]').click();
  const canvas=page.locator("#drawing");await canvas.scrollIntoViewIfNeeded();
  const box=await canvas.boundingBox();if(!box)throw Error("No canvas");
  await page.mouse.move(box.x+box.width*.25,box.y+box.height*.25);
  await page.mouse.down();await page.mouse.move(box.x+box.width*.7,box.y+box.height*.67,{steps:10});await page.mouse.up();
  check(name+" drawing produces stroke",await page.locator("#stroke-count").textContent().then(t=>t.includes("1 линия")));
  await page.locator("#guide").uncheck();
  check(name+" guide toggle",!await page.locator("#guide").isChecked());
  const promised=page.waitForEvent("download");
  await page.locator("#save").click();
  const download=await promised;
  check(name+" PNG export",download.suggestedFilename().endsWith(".png"));
  check(name+" no academy JS errors",errors.length===0);
  await page.screenshot({path:outDir+"/"+name+"-drawing.jpg",type:"jpeg",quality:70,fullPage:true});
  await ctx.close();
 }
 }finally{await browser.close();}
 fs.writeFileSync(outDir+"/qa_ateliers.json",JSON.stringify(results,null,2));
 if(results.some(x=>!x.pass))process.exitCode=1;
}
run().catch(e=>{console.error(e);process.exitCode=1;});