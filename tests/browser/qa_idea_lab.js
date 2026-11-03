/* CI browser checks for three independent museum workflows; no network services beyond local static server. */
"use strict";
const {chromium}=require("playwright");
const fs=require("fs");
const [,,origin,outDir]=process.argv;
if(!origin||!outDir)throw Error("Usage: qa_idea_lab.js <origin> <screens>");
fs.mkdirSync(outDir,{recursive:true});
const results=[];function check(label,ok){const pass=!!ok;console.log((pass?"PASS ":"FAIL ")+label);results.push([label,pass]);}
async function go(page,path){return page.goto(new URL(path,origin).href,{waitUntil:"domcontentloaded"});}
async function noScroll(page,label){check(label+" no horizontal overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));}
(async()=>{const browser=await chromium.launch({headless:true});try{
for(const [label,w,h] of [["phone-390",390,844],["ipad-820",820,1180],["desktop-1440",1440,900]]){
 const ctx=await browser.newContext({viewport:{width:w,height:h},acceptDownloads:true});
 const page=await ctx.newPage(),errors=[];page.on("pageerror",e=>errors.push(e.message));
 const r1=await go(page,"ideas/");
 check(label+" idea radar HTTP200",r1.status()===200);
 await page.waitForFunction(()=>document.querySelectorAll("#ideas .idea").length===14,{timeout:15000});
 check(label+" 14 reviewed ideas",await page.locator("#ideas .idea").count()===14);
 check(label+" three source-led schemes",await page.locator("#schemeGrid .schema").count()===3);
 await noScroll(page,label+" radar");
 await page.locator("#status").selectOption("pilot");
 check(label+" pilot filtering",await page.locator("#ideas .idea").count()===2);
 await page.locator("#reset").click();
 await page.locator("#search").fill("литографский камень");
 check(label+" full text search",await page.locator("#ideas .idea").count()===1);
 await page.locator("#reset").click();
 await page.screenshot({path:outDir+"/"+label+"-ideas.jpg",type:"jpeg",quality:68,fullPage:true});
 const r2=await go(page,"printlab/");
 check(label+" printlab HTTP200",r2.status()===200);
 check(label+" six stages",await page.locator("#stages .stage").count()===6);
 check(label+" genuine LoC artwork",await page.locator("img[src*='madeleine-historic-loc']").count()===1);
 await noScroll(page,label+" printlab");
 await page.locator("#stone").scrollIntoViewIfNeeded();
 const box=await page.locator("#stone").boundingBox();if(!box)throw Error("Missing lithography canvas");
 await page.mouse.move(box.x+box.width*.29,box.y+box.height*.39);
 await page.mouse.down();await page.mouse.move(box.x+box.width*.68,box.y+box.height*.58,{steps:10});await page.mouse.up();
 check(label+" pencil stroke recorded",await page.locator("#strokeCount").textContent().then(s=>s.includes("1")));
 await page.reload({waitUntil:"domcontentloaded"});
 check(label+" sketch survives reload",await page.locator("#strokeCount").textContent().then(s=>s.includes("1")));
 await page.locator("#undo").click();
 check(label+" undo user drawing",await page.locator("#strokeCount").textContent().then(s=>s.includes("0")));
 for(let k=0;k<5;k++)await page.locator("#next").click();
 check(label+" finished stone press process",await page.locator("#stepHeading").textContent().then(s=>s.includes("тираж")));
 check(label+" last stage selected",await page.locator('.stage[aria-current="true"]').getAttribute("data-step").then(x=>x==="5"));
 const [pn]=await Promise.all([page.waitForEvent("download"),page.locator("#export").click()]);
 check(label+" PNG study print exported",pn.suggestedFilename()==="city-on-paper-study-lithograph.png");
 await page.screenshot({path:outDir+"/"+label+"-printlab.jpg",type:"jpeg",quality:70,fullPage:true});
 const r3=await go(page,"fieldwork/");
 check(label+" fieldwork HTTP200",r3.status()===200);
 await page.waitForFunction(()=>document.querySelector("#old").naturalWidth>0 && document.querySelector("#modern").naturalWidth>0);
 check(label+" historical and modern images load",await page.locator("#old").evaluate(x=>x.naturalWidth>100) && await page.locator("#modern").evaluate(x=>x.naturalWidth>100));
 await noScroll(page,label+" fieldwork");
 await page.locator("#place").selectOption("palais");
 await page.waitForFunction(()=>document.querySelector("#old").getAttribute("src").includes("palais-royal"));
 check(label+" second verified monument",await page.locator("#oldCaption").textContent().then(x=>x.includes("pga-14314")));
 // A synthetic 1px PNG, never a real user's image.
 const testPng=Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAMAAAADCAIAAADZSiLoAAAAF0lEQVR4nGOsWBrFwMDAwMDAxAADCBYAKZoBfchCQtYAAAAASUVORK5CYII=","base64");
 await page.locator("#upload").setInputFiles({name:"my-test-photo.png",mimeType:"image/png",buffer:testPng});
 await page.waitForFunction(()=>document.querySelector("#photoKind").textContent.includes("Личный снимок"));
 check(label+" local upload stays on device",await page.locator("#modern").getAttribute("src").then(x=>x.startsWith("blob:")));
 await page.locator("#notes").fill("Колонны сохранились; ракурс и фон отличаются.");
 await page.locator('[data-check="landmark"]').check();
 check(label+" fieldwork progress",await page.locator("#progress").textContent().then(x=>x.startsWith("1 из 4")));
 const [jdownload]=await Promise.all([page.waitForEvent("download"),page.locator("#save").click()]);
 const contents=fs.readFileSync(await jdownload.path(),"utf8");const notes=JSON.parse(contents);
 check(label+" JSON exported with no photo or GPS",contents.includes("User image (not included)")&&!contents.includes("data:image")&&!contents.includes("GPS:")&&notes.notes.includes("Колонны"));
 const [pdownload]=await Promise.all([page.waitForEvent("download"),page.locator("#picture").click()]);
 check(label+" comparison PNG exported",pdownload.suggestedFilename().endsWith(".png"));
 await page.reload({waitUntil:"domcontentloaded"});
 check(label+" private notes persist",await page.locator("#notes").inputValue().then(x=>x.includes("Колонны")));
 check(label+" no media uploaded on reload",await page.locator("#modern").getAttribute("src").then(x=>!x.startsWith("blob:")));
 await page.locator("#wipe").click();
 check(label+" notes removable",await page.locator("#notes").inputValue().then(x=>!x));
 check(label+" no runtime errors",errors.length===0);
 await page.screenshot({path:outDir+"/"+label+"-fieldwork.jpg",type:"jpeg",quality:70,fullPage:true});
 await ctx.close();
}
const home=await browser.newPage();await go(home,"");
check("home links all three new rooms",(await home.locator('a[href="ideas/"]').count())>0&&(await home.locator('a[href="printlab/"]').count())>0&&(await home.locator('a[href="fieldwork/"]').count())>0);
await home.close();
}finally{await browser.close()}
fs.writeFileSync(outDir+"/qa_idea_lab.json",JSON.stringify(results,null,2));console.log(results.length+" checks, "+results.filter(x=>!x[1]).length+" failures");if(results.some(x=>!x[1]))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});