/* Multi-viewport WCAG 2.2 AA + best-practice audit for the actual museum.
 * Accessibility automation cannot replace real Safari/VoiceOver evaluation.
 * Emits inspectable reports, no invented "accessible" badge.
 */
"use strict";
const { chromium } = require("playwright");
const AxeBuilder = require("@axe-core/playwright").default;
const fs = require("fs");
const [, , origin, output] = process.argv;
if (!origin || !output) throw Error("Usage: qa_museum_a11y.js <origin> <directory>");
const locations = [
  ["home", ""],
  ["world", "world/"],
  ["atlas", "eras/"],
  ["paris", "eras/#/city/paris"],
  ["venice", "exhibitions/city-as-evidence/"],
];
const sizes = [
  ["mobile-390", 390, 844],
  ["tablet-820", 820, 1180],
  ["desktop-1440", 1440, 900],
];
const escapeMd = s => String(s || "").replace(/[|\n\r]/g, " ");
async function main() {
  const browser = await chromium.launch({ headless: true });
  const reports = [];
  try {
    for (const [viewport, width, height] of sizes) {
      const context = await browser.newContext({
        viewport: { width, height },
        isMobile: viewport === "mobile-390",
        hasTouch: viewport === "mobile-390",
        reducedMotion: viewport === "mobile-390" ? "reduce" : "no-preference",
      });
      const page = await context.newPage();
      try {
        for (const [label, path] of locations) {
          const url = new URL(path, origin).href;
          const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
          // Changing only the #/city route does not request a new HTML page:
          // Playwright correctly returns null for same-document navigation.
          if ((response && response.status() !== 200) ||
              (!response && !url.includes("#"))) {
            throw Error("Missing page: " + url + ": " + response?.status());
          }
          await page.locator("#museumBar").waitFor({ state: "attached", timeout: 10000 });
          if (label === "paris") {
            await page.waitForFunction(() =>
              document.querySelector("h1")?.textContent?.includes("Париж"),
            null, { timeout: 12000 });
            await page.locator("#historicCartography h3").waitFor();
          }
          const checks = await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa",
              "best-practice"])
            .analyze();
          const violations = checks.violations.map(v => ({
            id: v.id, impact: v.impact, description: v.description,
            help: v.help, helpUrl: v.helpUrl,
            nodes: v.nodes.slice(0, 12).map(n => ({
              target: n.target, summary: n.failureSummary?.slice(0, 550),
            })),
            affected_nodes: v.nodes.length,
          }));
          reports.push({
            viewport, width, height, label, url,
            violations, incomplete_count: checks.incomplete.length,
            passes_count: checks.passes.length,
          });
          const errors = violations.filter(v => v.impact === "critical" || v.impact === "serious");
          console.log(viewport + " " + label + ": " +
            violations.length + " rule violations, " + errors.length +
            " serious/critical, " + checks.incomplete.length + " needs human review");
        }
      } finally {
        await page.close();
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }
  fs.mkdirSync(output, { recursive: true });
  const totals = { screens: reports.length, violations: 0, high: 0,
    needs_manual_review: 0, unique_rules: [] };
  const ids = new Set();
  for (const page of reports) {
    totals.violations += page.violations.length;
    totals.high += page.violations.filter(v =>
      ["critical", "serious"].includes(v.impact)).length;
    totals.needs_manual_review += page.incomplete_count;
    for (const issue of page.violations) ids.add(issue.id);
  }
  totals.unique_rules = [...ids].sort();
  const result = {
    tool: "@axe-core/playwright@4.14.0",
    standard: "WCAG 2.2 A/AA plus axe best practices",
    limitations: "Automated scans only; no live Safari/VoiceOver or actual art historical review",
    totals, pages: reports,
  };
  fs.writeFileSync(output + "/axe-consilium-audit.json", JSON.stringify(result, null, 2));
  const rows = reports.flatMap(p => p.violations.map(v => (
    "| " + escapeMd(p.viewport) + " | " + escapeMd(p.label) + " | " +
    escapeMd(v.impact) + " | " + escapeMd(v.id) + " | " + v.affected_nodes +
    " | " + escapeMd(v.help) + " |"
  )));
  const markdown = [
    "# Автоматический аудит доступности City on Paper",
    "",
    "Проверено страниц: **" + totals.screens + "**. Нарушения правил на экранах: **" +
      totals.violations + "**; серьёзные и критические: **" + totals.high +
      "**; требующие ручной проверки: **" + totals.needs_manual_review + "**.",
    "",
    "Браузер: Chromium Playwright. WCAG 2.2 A/AA + axe best practices. " +
      "Это не независимое тестирование на физическом iPhone Safari и не сертификат WCAG.",
    "",
    "| Экран | Страница | Влияние | Правило | Элементы | Проблема |",
    "| --- | --- | --- | --- | ---: | --- |",
    ...rows,
    "",
    "Все селекторы, пояснения и прямые ссылки на правила: axe-consilium-audit.json.",
  ].join("\n");
  fs.writeFileSync(output + "/axe-consilium-audit.md", markdown);
  console.log("CONSILIUM SUMMARY: " + JSON.stringify(totals));
  // Advisory evidence until defects are triaged. A separate release gate
  // must require owner/QA acknowledgement for unresolved serious items.
}
main().catch(err => { console.error(err.stack); process.exitCode = 1; });
