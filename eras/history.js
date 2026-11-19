/* Город на бумаге — «История города» и «Мастера».
 * Тексты: data/history.json (историк-редактор; у каждой главы и даты — ссылка на источник).
 * Модуль только показывает то, что есть в данных, и ничего не дописывает. */
"use strict";
window.History = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const link = (u) => (/^https:\/\//.test(u || "") ? u : "");
  const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return "источник"; } };
  let H = null;
  const load = () => H ? Promise.resolve(H) : fetch("data/history.json").then((r) => (r.ok ? r.json() : { cities: [], masters: [] }))
    .catch(() => ({ cities: [], masters: [] })).then((d) => (H = d));
  const src = (list) => (list || []).filter((s) => link(s.url)).map((s) =>
    `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title || host(s.url))} ↗</a>`).join(" · ");

  function city(host_, name) {
    if (!host_) return;
    load().then((d) => {
      const c = (d.cities || []).find((x) => x.city === name);
      if (!c) { host_.hidden = true; return; }
      host_.hidden = false;
      host_.innerHTML = `<span class="eyebrow">История города</span>
        <h2 class="hist-tag">${esc(c.tagline || name)}</h2>
        <p class="lede">${esc(c.intro || "")}</p>
        <div class="hist-ch">${(c.chapters || []).map((ch, i) => `<details class="hist-chapter" ${i === 0 ? "open" : ""}>
          <summary><b>${esc(ch.title)}</b></summary><p>${esc(ch.text)}</p>
          <p class="hist-src">Источники: ${src(ch.sources) || "уточняются"}</p></details>`).join("")}</div>
        ${(c.timeline || []).length ? `<ol class="hist-time" aria-label="Хронология">${c.timeline.map((t) =>
          `<li><b>${esc(t.year)}</b><span>${esc(t.text)}${link(t.source_url) ? ` <a href="${esc(t.source_url)}" target="_blank" rel="noopener" aria-label="Источник: ${esc(host(t.source_url))}">↗</a>` : ""}</span></li>`).join("")}</ol>` : ""}
        ${c.did_you_know && c.did_you_know.text ? `<p class="hist-fact"><b>А вы знали?</b> ${esc(c.did_you_know.text)}${link(c.did_you_know.source_url) ? ` <a href="${esc(c.did_you_know.source_url)}" target="_blank" rel="noopener">источник ↗</a>` : ""}</p>` : ""}
        <p class="mapnote">Текст составлен по открытым источникам, ссылки приведены у каждой главы. Заметили неточность — напишите через «Отзыв».</p>`;
    });
  }

  function masters(app) {
    load().then((d) => {
      const ms = d.masters || [];
      app.innerHTML = `<div class="view"><nav class="crumbs" aria-label="Путь"><a href="#/">Атлас</a> › <span aria-current="page">Мастера</span></nav>
        <span class="eyebrow">Кто сделал эти листы</span><h1>Мастера и техники</h1>
        <p class="lede">Рисовальщики, литографы, печатники и издатели, чьи имена стоят под листами музея, и техники, которыми эти листы сделаны. Спорные и неустановленные сведения отмечены отдельно.</p>
        ${ms.length ? `<div class="masters">${ms.map((m) => `<article class="master"><h2>${esc(m.name_ru || m.name)}</h2>
          <p class="mrole">${esc([m.name_ru && m.name !== m.name_ru ? m.name : "", m.years, m.role].filter(Boolean).join(" · "))}</p>
          <p>${esc(m.bio)}</p>${m.uncertain ? `<p class="hist-fact"><b>Не установлено:</b> ${esc(m.uncertain)}</p>` : ""}
          <p class="hist-src">Источники: ${src(m.sources) || "уточняются"}</p></article>`).join("")}</div>` : '<p class="note">Справки о мастерах готовятся.</p>'}</div>`;
    });
  }
  return { city, masters, load };
})();
