"use strict";

const assert = require("node:assert/strict");
const {chromium} = require("playwright");
const base = process.argv[2];

(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    for (const width of [320, 390, 820, 1440]) {
      const page = await browser.newPage({viewport: {width, height: 900}, reducedMotion: "reduce"});
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.goto(base);
      assert(await page.locator(".wow-secondary").isVisible());
      assert((await page.locator(".wow-secondary").getAttribute("href")) === "book/");
      await page.goto(new URL("guides/", base).href);
      await page.locator("#vasi-rome-1763").waitFor();
      const cards = page.locator("#books .book");
      const count = await cards.count();
      assert(count >= 8);
      const book = page.locator("#vasi-rome-1763");
      assert((await book.getByRole("link", {name: "Листать в архиве"}).getAttribute("href")).startsWith("https://"));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.locator("#query").fill("вАзИ");
      assert(await cards.count() < count);
      assert(await book.isVisible());
      await page.locator("#kind").selectOption("view-series");
      assert(await book.isHidden());
      await page.reload();
      assert.equal(await page.locator("#query").inputValue(), "вАзИ");
      await page.locator(".book").first().waitFor();
      const detail = page.locator(".book details").first();
      await detail.locator("summary").click();
      assert(await detail.locator("li a").count() >= 3);
      await page.locator("#query").fill("Нет такого путеводителя");
      assert.match(await page.locator("#status").innerText(), /изданий пока нет/);
      await page.goto(new URL("guides/#vasi-rome-1763", base).href);
      await book.getByRole("link", {name: "Сравнить с фото"}).click();
      await page.locator('[data-view="originals"][aria-pressed="true"]').waitFor();
      assert(await page.locator("#handle").isVisible());
      assert(await page.locator('[data-view="fit"]').getAttribute("aria-disabled") === "true");
      await page.locator("#pairMap").click();
      await page.getByRole("heading", {name: "Пантеон", exact: false}).first().waitFor();
      await page.goto(new URL("guides/#benoist", base).href);
      const samples = page.locator(".plate-grid img");
      assert(await samples.count() >= 3);
      assert(await samples.evaluateAll(async images => {
        for (const image of images) { image.scrollIntoView({block: "center"}); await image.decode(); }
        return images.every(image => image.naturalWidth > 200);
      }));
      assert.deepEqual(errors, []);
      console.log(`PASS guides ${width}px: books, filters, volumes, Pantheon comparison and map, Benoist plates`);
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
