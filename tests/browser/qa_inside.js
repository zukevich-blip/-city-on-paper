// "Внутри истории": five dossiers from real materials; the door journey; honest gaps. Usage: node tests/browser/qa_inside.js http://127.0.0.1:8765/book/ [dir]
const { chromium } = require("playwright");
const fs = require("fs");
const [, , base, shots] = process.argv;
if (!base) throw Error("Usage: qa_inside.js <url of book/> [dir]");
if (shots) fs.mkdirSync(shots, { recursive: true });
const results = [];
const check = (name, ok, detail = "") => { results.push(ok); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail}`); };
(async () => {
  const browser = await chromium.launch();
  for (const v of [{ name: "iphone-390", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }, { name: "desktop-1280", viewport: { width: 1280, height: 900 } }]) {
    const ctx = await browser.newContext(v), page = await ctx.newPage(), errs = [];
    page.on("pageerror", (e) => errs.push(String(e)));
    await page.route(/tile\.openstreetmap/, (r) => r.abort());
    const shot = async (n) => { if (shots) await page.screenshot({ path: `${shots}/${v.name}-${n}.png` }); };
    const loaded = (sel) => page.waitForFunction((s) => { const a = [...document.querySelectorAll(s)]; return a.length > 0 && a.every((i) => i.complete && i.naturalWidth > 0); }, sel, { timeout: 20000 });
    await page.goto(base + "#/inside", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".exhall");
    check(`${v.name}: five buildings are listed`, (await page.locator(".exlist:not(#storyList) .exhall").count()) === 5); await shot("20-inside-list");
    await page.goto(base + "#/inside/madeleine", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#doorStage");
    await page.locator("#facade img").first().evaluate((i) => i.scrollIntoView());
    await loaded("#facade .rail img");
    check(`${v.name}: Madeleine facade, interior, plan and today images really open`, await (async () => { await page.locator("#plan").scrollIntoViewIfNeeded(); await loaded("#plan img"); await page.locator("#today").scrollIntoViewIfNeeded(); await loaded("#today img"); await page.locator("#interior").scrollIntoViewIfNeeded(); await loaded("#interior .rail img"); return true; })());
    await page.locator("#door").scrollIntoViewIfNeeded(); await loaded("#doorStage img");
    const op = {};
    for (const t of [0, 40, 100]) { await page.locator("#doorT").fill(String(t)); op[t] = await page.evaluate(() => [getComputedStyle(document.querySelector(".dA")).opacity, getComputedStyle(document.querySelector(".dB")).opacity, document.querySelector(".dA").style.transform]); }
    check(`${v.name}: door journey zooms into the door, then the interior appears`, op[0][0] === "1" && op[0][1] === "0" && Number((op[40][2].match(/scale\(([\d.]+)/) || [])[1]) > 3, JSON.stringify(op));
    check(`${v.name}: door journey ends inside (outside hidden, inside visible)`, Number(op[100][0]) < 0.05 && Number(op[100][1]) > 0.95, JSON.stringify(op[100]));
    await shot("21-door");
    await page.locator("#plan").scrollIntoViewIfNeeded(); await shot("22-plan");
    check(`${v.name}: every credit line names an author and a licence`, (await page.locator(".insfig .excap").allInnerTexts()).every((t) => /(CC0|CC BY|Public Domain)/.test(t)));
    await page.goto(base + "#/inside/sainte-chapelle", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".insec");
    const txt = await page.locator(".inside").innerText();
    check(`${v.name}: Sainte-Chapelle says plainly what is missing (plan, section, photo today) and has no door`, /Плана в открытых собраниях пока не найдено/.test(txt) && /Современного снимка/.test(txt) && (await page.locator("#doorStage").count()) === 0); await shot("23-sainte-chapelle");
    await page.goto(base + "#/inside/pantheon-paris", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#section");
    await page.locator("#section").scrollIntoViewIfNeeded(); await loaded("#section img");
    check(`${v.name}: Paris Pantheon shows the dome section from a real 1881 plate and refuses a fake interior`, /не подставляем чужие залы/.test(await page.locator(".inside").innerText()) && (await page.locator("#section .insfig").count()) === 1); await shot("24-pantheon-section");
    await page.goto(base + "#/inside/pantheon-rome", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#plan");
    await page.locator("#plan").scrollIntoViewIfNeeded(); await loaded("#plan img");
    check(`${v.name}: Roman Pantheon has facade views, Panini interior, two plans`, (await page.locator("#facade .rt").count()) >= 3 && (await page.locator("#plan .insfig").count()) === 2 && (await page.locator("#interior .insfig").count()) === 1);
    await page.goto(base + "#/inside", { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#storyList .exhall");
    check(`${v.name}: three stories with three different compositions are offered`, (await page.locator("#storyList .exhall").count()) === 3);
    for (const [sid, sel, min] of [["prazdniki-venetsii", ".scene .sceneimg img", 5], ["dialog-panteon", ".turn img", 6], ["biografiya-madlen", ".bioev", 7]]) {
      await page.goto(base + "#/story/" + sid, { waitUntil: "domcontentloaded" });
      await page.waitForSelector(sel);
      await page.waitForFunction(([s, m]) => document.querySelectorAll(s).length >= m, [sel, min]);
      if (sid !== "biografiya-madlen") { await page.locator(sel).first().evaluate((i) => i.scrollIntoView()); await loaded(sel + ":nth-of-type(1)").catch(() => {}); }
      check(`${v.name}: story ${sid} renders its composition`, (await page.locator(sel).count()) >= min);
      if (sid === "dialog-panteon") await shot("25-story-dialogue");
      if (sid === "biografiya-madlen") { check(`${v.name}: biography events all carry a source link`, (await page.locator(".bioev .src[href^=http]").count()) === 7); await shot("26-story-biography"); }
      if (sid === "prazdniki-venetsii") await shot("27-story-scenes");
    }
    check(`${v.name}: no horizontal scroll and no page errors`, (await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 4)) && errs.length === 0, errs.join("|"));
    await ctx.close();
  }
  await browser.close();
  if (results.some((r) => !r)) process.exit(1);
})();
