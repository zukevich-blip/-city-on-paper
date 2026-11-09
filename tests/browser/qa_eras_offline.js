/* Exercise the real service worker in an isolated browser context. */
"use strict";
const { chromium } = require("playwright");
const fs = require("fs");
const [, , origin, outDir] = process.argv;
if (!origin || !outDir) throw Error("Usage: qa_eras_offline.js <origin> <out>");
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 }, serviceWorkers: "allow",
  });
  const page = await ctx.newPage();
  const results = [];
  const assert = (name, good, detail) => {
    results.push({ name, pass: Boolean(good), detail });
    if (!good) throw Error(name + ": " + JSON.stringify(detail));
  };
  try {
    await page.goto(new URL("eras/", origin).href, { waitUntil: "networkidle" });
    await page.evaluate(() => navigator.serviceWorker.ready);
    await page.reload({ waitUntil: "networkidle" });
    await page.waitForFunction(() => navigator.serviceWorker?.controller, null,
      { timeout: 15000 });
    const controller = await page.evaluate(() => navigator.serviceWorker.controller?.scriptURL);
    assert("installed SW controls /eras", controller.endsWith("/eras/sw.js"), controller);
    await ctx.setOffline(true);
    const offline = await page.evaluate(async () => {
      const targets = ["index.html", "journey.js", "data/atlas.json", "data/map-evidence.json",
        "missing-qa-service-worker-asset.js"];
      const checks = [];
      for (const url of targets) {
        const result = await fetch(url);
        const body = await result.text();
        checks.push({
          url, status: result.status,
          contentType: result.headers.get("Content-Type"),
          head: body.slice(0, 160),
        });
      }
      return checks;
    });
    const by = Object.fromEntries(offline.map(x => [x.url, x]));
    assert("offline home serves HTML", by["index.html"].status === 200
      && /<!doctype html/i.test(by["index.html"].head), by["index.html"]);
    assert("offline journey JS is real code", by["journey.js"].status === 200
      && by["journey.js"].head.includes("Editorial museum trail") && !by["journey.js"].head.includes("<html"),
      by["journey.js"]);
    assert("offline atlas JSON is JSON", by["data/atlas.json"].status === 200
      && by["data/atlas.json"].contentType.includes("json")
      && by["data/atlas.json"].head.trim().startsWith("{"), by["data/atlas.json"]);
    assert("offline map evidence JSON is real metadata",
      by["data/map-evidence.json"].status === 200
      && by["data/map-evidence.json"].head.includes("city-on-paper"),
      by["data/map-evidence.json"]);
    assert("uncached JS miss is an honest 404/503, never an HTML success",
      [404, 503].includes(by["missing-qa-service-worker-asset.js"].status)
      && /text\/plain/i.test(by["missing-qa-service-worker-asset.js"].contentType || "")
      && !/<html/i.test(by["missing-qa-service-worker-asset.js"].head),
      by["missing-qa-service-worker-asset.js"]);
    const cacheKeys = await page.evaluate(() => caches.keys());
    assert("service worker uses namespaced cache keys",
      cacheKeys.some(x => x.startsWith("city-on-paper-eras-")), cacheKeys);
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(outDir + "/pwa-offline-regression.json",
      JSON.stringify({ results, cached: cacheKeys, requests: offline }, null, 2));
    console.log("PASS: " + results.length + " offline PWA checks");
  } finally {
    await ctx.setOffline(false);
    await ctx.close();
    await browser.close();
  }
})().catch(e => { console.error(e.stack); process.exitCode = 1; });
