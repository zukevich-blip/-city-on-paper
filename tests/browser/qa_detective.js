const { chromium } = require("playwright");
const fs = require("fs");
const [, , url, directory] = process.argv;
if (!url || !directory) throw Error("Usage: node qa_detective.js <url> <dir>");
fs.mkdirSync(directory, {recursive:true});
async function run(){
 const browser=await chromium.launch();
 const checks=[];
 const test=(name,ok)=>{console.log((ok?"PASS ":"FAIL ")+name);checks.push({name,pass:!!ok});};
 try{
 for(const vp of [{name:"phone-390",width:390,height:844},{name:"tablet-820",width:820,height:1180},{name:"desktop-1440",width:1440,height:900}]){
  const ctx=await browser.newContext({viewport:{width:vp.width,height:vp.height},isMobile:vp.width<1000,hasTouch:vp.width<1000});
  const page=await ctx.newPage(); const errors=[];
  page.on("pageerror",e=>errors.push(e.message));
  await page.goto(url,{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelectorAll(".pin").length===5);
  test(vp.name+" five sourced hotspots",await page.locator(".pin").count()===5);
  test(vp.name+" no horizontal overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  test(vp.name+" correct original artwork",await page.locator(".artSurface img").evaluate(x=>x.complete&&x.naturalWidth>0));
  await page.locator('.pin[data-id="facade"]').click();
  test(vp.name+" architectural clue opens",await page.locator("#clueTitle").innerText()==="Фронтон и античный образ");
  await page.locator('[data-filter="life"]').click();
  test(vp.name+" life filter",await page.locator(".pin:visible").count()===1);
  await page.locator('[data-filter="all"]').click();
  await page.locator("#timeDial").evaluate(e=>{e.value="70";e.dispatchEvent(new Event("input",{bubbles:true}));});
  test(vp.name+" honest dual-image dial",await page.locator("#timePercent").innerText()==="70% / 30%");
  test(vp.name+" six sourced political events",await page.locator(".moment").count()===6);
  test(vp.name+" commissioner explicitly unknown",await page.locator(".evidence.unknown").count()===1);
  await page.locator("#quizAnswers button").nth(1).click();
  test(vp.name+" quiz correct answer",await page.locator(".answers .correct").count()===1);
  await page.locator("#quizNext").click();
  const quizStep=await page.locator("#quizProgress").textContent();console.log("QUIZ_STATUS "+vp.name+" "+JSON.stringify(quizStep));test(vp.name+" quiz moves",quizStep==="Вопрос 2 из 3");
  test(vp.name+" no JS errors",errors.length===0);
  await page.screenshot({path:directory+"/"+vp.name+"-detective.jpg",type:"jpeg",quality:70,fullPage:true});
  await ctx.close();
 }
 }finally{await browser.close();}
 fs.writeFileSync(directory+"/qa_detective.json",JSON.stringify(checks,null,2));
 if(checks.some(c=>!c.pass))process.exitCode=1;
}
run().catch(e=>{console.error(e);process.exitCode=1;});
