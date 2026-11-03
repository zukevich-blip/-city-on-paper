const { chromium }=require("playwright");
const fs=require("fs");
const [,,url,outDir]=process.argv;
if(!url||!outDir)throw Error("Usage: node qa_studio.js <url> <outDir>");
fs.mkdirSync(outDir,{recursive:true});
const checks=[];
function check(n,yes){checks.push({name:n,pass:!!yes});console.log((yes?"PASS ":"FAIL ")+n);}
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
 for(const vp of [{name:"iphone-390",width:390,height:844},{name:"ipad-820",width:820,height:1180},{name:"desktop-1440",width:1440,height:900}]){
  const context=await browser.newContext({viewport:{width:vp.width,height:vp.height},isMobile:vp.width<1000,hasTouch:vp.width<1000,acceptDownloads:true});
  const page=await context.newPage(),errors=[];
  page.on("pageerror",e=>errors.push(e.message));
  await page.goto(url,{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelectorAll("#workChoices .work").length===2);
  check(vp.name+" two verified plates",await page.locator("#workChoices .work").count()===2);
  check(vp.name+" no viewport overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  check(vp.name+" actual LoC image visible",await page.locator("#workChoices img").first().evaluate(x=>x.complete&&x.naturalWidth>0));
  check(vp.name+" clear unverified patron",await page.locator(".node").last().innerText().then(x=>x.includes("заказчик")));
  await page.locator("#agentNodes .node").nth(1).click();
  check(vp.name+" printer source is clickable",await page.locator("#agentEvidence a").count()===2);
  await page.locator("#workChoices .work").nth(1).click();
  check(vp.name+" independent art passport",await page.locator("#selectedTitle").innerText()==="Paris. Jardin du Palais Royal");
  check(vp.name+" researched plate 6",await page.locator("#passport").innerText().then(t=>t.includes("LC-DIG-pga-14314")));
  await page.locator("#privateNotes").fill("Проверить архивные записи Lemercier: эскиз и цена. — notes test");
  await page.locator("#researchStatus").selectOption("research");
  await page.locator('#checklist input[type="checkbox"]').first().check();
  await page.locator("#saveNotes").click();
  await page.reload({waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelectorAll("#workChoices .work").length===2);
  await page.locator("#workChoices .work").nth(1).click();
  check(vp.name+" private note persisted",await page.locator("#privateNotes").inputValue()==="Проверить архивные записи Lemercier: эскиз и цена. — notes test");
  check(vp.name+" checkbox and stage persisted",await page.locator("#researchStatus").inputValue()==="research"&&await page.locator('#checklist input[type="checkbox"]').first().isChecked());
  const downloadPromise=page.waitForEvent("download");
  await page.locator("#exportJson").click();
  const download=await downloadPromise;
  check(vp.name+" JSON export created",download.suggestedFilename()==="City-on-Paper-notebook.json");
  const path=await download.path();
  const obj=JSON.parse(fs.readFileSync(path,"utf8"));
  check(vp.name+" exported normalized source notes",obj.kind==="city-on-paper-notebook"&&obj.notes.palais_royal?.status==="research");
  const before=await page.locator("#privateNotes").inputValue();
  page.once("dialog",d=>d.accept());
  await page.locator("#restoreArchive").setInputFiles(path);
  check(vp.name+" safe JSON import",await page.locator("#privateNotes").inputValue()===before);
  check(vp.name+" no JavaScript errors",errors.length===0);
  await page.screenshot({path:outDir+"/"+vp.name+"-studio.jpg",type:"jpeg",quality:72,fullPage:true});
  await context.close();
 }
 }finally{await browser.close();}
 fs.writeFileSync(outDir+"/qa_studio.json",JSON.stringify(checks,null,2));
 if(checks.some(x=>!x.pass))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
