const {chromium}=require("playwright");
const fs=require("fs");
const [,,base,out]=process.argv;
if(!base||!out)throw Error("Usage: qa_discover.js <url> <screenshots>");
fs.mkdirSync(out,{recursive:true});
const results=[];
function check(n,val){const ok=!!val;results.push({name:n,pass:ok});console.log((ok?"PASS ":"FAIL ")+n);}
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
 for(const vp of [{name:"phone-390",width:390,height:844},{name:"tablet-820",width:820,height:1180},{name:"desktop-1440",width:1440,height:900}]){
 const ctx=await browser.newContext({viewport:{width:vp.width,height:vp.height},isMobile:vp.width<950,hasTouch:vp.width<950});
 const page=await ctx.newPage(),errs=[];page.on("pageerror",e=>errs.push(e.message));
 const response=await page.goto(base,{waitUntil:"domcontentloaded"});
 await page.waitForFunction(()=>document.querySelectorAll("#hotspots .pin").length===5);
 check(vp.name+" 200",response.status()===200);
 check(vp.name+" no horizontal scroll",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 check(vp.name+" authentic historic image",await page.locator(".heroVisual img").evaluate(e=>e.complete&&e.naturalWidth>0));
 check(vp.name+" five annotated details",await page.locator("#hotspots .pin").count()===5);
 await page.locator("#hotspots .pin").nth(3).click();
 check(vp.name+" lithographic technique opens",await page.locator("#clueTitle").innerText()==="Рисунок, камень, ручной цвет");
 check(vp.name+" source link present",await page.locator("#clueSource").getAttribute("href").then(x=>x.startsWith("https://www.loc.gov/")));
 await page.locator("#next").click();
 check(vp.name+" next clue works",await page.locator("#clueProgress").innerText()==="5 из 5");
 await page.locator("#answers button").nth(1).click();
 check(vp.name+" correct evidence response",await page.locator("#answers button.correct").count()===1);
 await page.locator("#quizNext").click();
 const quizState=await page.locator("#quizCount").textContent(); console.log("QUIZ_STATE "+vp.name+" "+JSON.stringify(quizState));
 check(vp.name+" quiz changes question",quizState==="Вопрос 2 из 3");
 await page.locator('[data-path="collector"]').click();
 check(vp.name+" collector path links notebook",await page.locator("#pathGo").getAttribute("href")==="../studio/");
 check(vp.name+" shareable permalink path",new URL(page.url()).searchParams.get("path")==="collector");
 check(vp.name+" no JS errors",errs.length===0);
 await page.screenshot({path:out+"/"+vp.name+"-discovery.jpg",type:"jpeg",quality:75,fullPage:true});
 await ctx.close();
 }
 }finally{await browser.close();}
 fs.writeFileSync(out+"/qa_discover.json",JSON.stringify(results,null,2));
 if(results.some(x=>!x.pass))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});