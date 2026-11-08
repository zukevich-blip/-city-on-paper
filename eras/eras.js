/* Атлас эпох — прототип (Issue #34). Vanilla JS, без зависимостей.
 * Правила: исторические изображения не трансформируются (никаких transform/filter на них);
 * современное фото не деформируется; оценка совпадения ракурса берётся из данных и показывается всегда. */
"use strict";
(() => {
  const app = document.getElementById("app");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = (u) => (/^https:\/\//.test(u || "") || /^img\//.test(u || "") ? u : "#");
  const KIND = { print: "Литография / гравюра", photo: "Фотография", photochrom: "Фотохром", today: "Сегодня", map: "Карта" };
  const VERDICT = {
    close: "Ракурс близок: та же точка и направление в пределах указанной погрешности (оценено вручную).",
    partial: "Ракурс частично совпадает: тот же объект, но точка или направление отличаются. Сравнивайте как свидетельства, а не как наложение.",
    different_viewpoint: "Ракурсы разные: точное наложение невозможно. Показываем рядом и честно отмечаем расхождение.",
    unknown: "Совпадение ракурса не оценивалось.",
  };
  let D = null;

  const rightsBadge = (img) => img.rights_class === "open"
    ? `<span class="rights open" title="${esc(img.rights)}">права проверены · ${esc(img.rights_short || "открыто")}</span>`
    : `<span class="rights link" title="${esc(img.rights)}">только ссылка · ${esc(img.rights_short || "ограничения")}</span>`;

  const credits = (img) => `<dl class="kv">
    <dt>Название</dt><dd>${esc(img.title)}</dd>
    <dt>Авторы</dt><dd>${esc((img.creators || []).filter((c) => c.name).map((c) => c.role ? `${c.name} (${c.role})` : c.name).join("; ") || "не указаны хранителем")}</dd>
    <dt>Дата</dt><dd>${esc(img.date)}</dd>
    <dt>Хранитель</dt><dd>${esc(img.institution)}</dd>
    <dt>Права</dt><dd>${esc(img.rights)}${img.rights_checked ? ` (проверено ${esc(img.rights_checked)})` : ""}${img.license_url ? ` · <a href="${esc(safeUrl(img.license_url))}" target="_blank" rel="noopener">текст лицензии ↗</a>` : ""}</dd>
    <dt>Карточка</dt><dd><a href="${esc(safeUrl(img.object_url))}" target="_blank" rel="noopener">открыть у хранителя ↗</a></dd>
    ${img.file ? `<dt>Файл</dt><dd><a href="${esc(safeUrl(img.file))}" target="_blank" rel="noopener">открыть без изменений</a>${img.note ? ` · ${esc(img.note)}` : ""}</dd>` : ""}
  </dl>`;

  function crumbs(parts) {
    return `<nav class="crumbs" aria-label="Путь">${parts.map((p, i) => i < parts.length - 1
      ? `<a href="${p[1]}">${esc(p[0])}</a> ›` : `<span aria-current="page">${esc(p[0])}</span>`).join(" ")}</nav>`;
  }

  // ---------------- portal
  function portal() {
    const P = D.portal;
    const pins = D.cities.map((c) => {
      const pos = P.pins[c.id];
      if (!pos) return "";
      const ready = c.places && c.places.length;
      return `<a class="pin" href="#/city/${esc(c.id)}" style="left:${pos.x / P.width * 100}%;top:${pos.y / P.height * 100}%"
        ${ready ? "" : 'aria-disabled="true"'} aria-label="${esc(c.name)}${ready ? "" : " — материалы готовятся"}"><i></i><span>${esc(c.name)}</span></a>`;
    }).join("");
    const eras = D.eras.map((e) => `<button aria-pressed="false" ${e.available ? "" : "disabled"} data-era="${esc(e.id)}"
      title="${esc(e.available ? e.hint : "нет подтверждённых материалов")}">${esc(e.label)}</button>`).join("");
    app.innerHTML = `<div class="view">
      <span class="eyebrow">Атлас эпох · вход через старую карту</span>
      <h1>Найдите город на старой карте<br>и пройдите сквозь время</h1>
      <p class="lede">Подлинная карта — это портал, а не навигатор: её геометрия XVIII века неточна, поэтому точки городов поставлены по самой карте. Внутри города — геопривязанный план и точки, откуда смотрели художник, фотограф и наш современник.</p>
      <div class="eras" role="group" aria-label="Эпохи">${eras}</div>
      <figure class="plate"><div class="frame"><img src="${esc(P.image)}" ${P.image_small ? `srcset="${esc(P.image_small)} 1000w, ${esc(P.image)} 2000w" sizes="(max-width: 700px) 100vw, 1400px"` : ""} width="${P.width}" height="${P.height}" alt="${esc(P.alt)}" fetchpriority="high">
        <div class="pins">${pins}</div></div>
        <figcaption>${esc(P.title)} — ${esc(P.credit)}. ${rightsBadge(P)} <a href="${esc(safeUrl(P.object_url))}" target="_blank" rel="noopener">карточка ↗</a>. Декоративная карта: расстояния и очертания не точны.</figcaption></figure>
      <p class="note" id="eraStatus" role="status" aria-live="polite">Выберите эпоху, чтобы увидеть города с подтверждёнными материалами.</p>
      <h2>Города</h2>
      <div class="cities">${D.cities.map((c) => `<a class="card" href="#/city/${esc(c.id)}"><span class="eyebrow">${esc(c.country)}</span><h3>${esc(c.name)}</h3><p>${esc(c.summary)}</p><small>${c.places.length} мест · ${c.places.reduce((n, p) => n + p.images.length, 0)} записей с источниками</small></a>`).join("")}</div>
    </div>`;
    app.querySelectorAll(".eras button").forEach((b) => b.addEventListener("click", () => {
      const on = b.getAttribute("aria-pressed") !== "true";
      app.querySelectorAll(".eras button").forEach((x) => x.setAttribute("aria-pressed", "false"));
      b.setAttribute("aria-pressed", String(on));
      app.querySelectorAll(".pin").forEach((pin) => {
        const id = pin.getAttribute("href").split("/").pop();
        const city = D.cities.find((c) => c.id === id);
        const has = !on || city.places.some((p) => p.images.some((i) => i.era === b.dataset.era));
        pin.style.opacity = has ? "1" : ".35";
      });
      const names = D.cities.filter((c) => c.places.some((p) => p.images.some((i) => i.era === b.dataset.era))).map((c) => c.name);
      document.getElementById("eraStatus").textContent = on
        ? `Эпоха «${b.textContent}»: материалы есть для ${names.length ? names.join(", ") : "ни одного города"}.`
        : "Показаны все города.";
    }));
  }

  // ---------------- city
  function camMarker(img, plan) {
    const c = img.camera;
    if (!c || c.px == null) return "";
    const az = (c.azimuth_on_plan ?? c.azimuth_deg ?? 0);
    const r = 34, half = 22 * Math.PI / 180, t = (az - 90) * Math.PI / 180;
    const p1 = [22 + r * Math.cos(t - half), 22 + r * Math.sin(t - half)], p2 = [22 + r * Math.cos(t + half), 22 + r * Math.sin(t + half)];
    return `<span class="cam era-${esc(img.era)}" aria-hidden="true" style="left:${c.px / plan.width * 100}%;top:${c.py / plan.height * 100}%" title="${esc(img.year_label)} · ${esc(img.title)}">
      <svg width="44" height="44" aria-hidden="true"><path class="cone" d="M22 22 L${p1[0].toFixed(1)} ${p1[1].toFixed(1)} L${p2[0].toFixed(1)} ${p2[1].toFixed(1)} Z"/><circle class="dot" cx="22" cy="22" r="6"/></svg></span>`;
  }

  function city(id) {
    const c = D.cities.find((x) => x.id === id);
    if (!c) return notFound();
    const P = c.plan;
    const pts = c.places.filter((pl) => pl.plan_xy);
    const left = (pl) => pts.some((o) => o !== pl && o.plan_xy[0] > pl.plan_xy[0] && (o.plan_xy[0] - pl.plan_xy[0]) / P.width < 0.25 && Math.abs(o.plan_xy[1] - pl.plan_xy[1]) / P.height < 0.12);
    const cams = P ? pts.map((pl) => `<a class="pin${left(pl) ? " left" : ""}" href="#/place/${esc(pl.id)}" style="left:${pl.plan_xy[0] / P.width * 100}%;top:${pl.plan_xy[1] / P.height * 100}%" aria-label="${esc(pl.title)}"><i></i><span>${esc(pl.short || pl.title)}</span></a>`).join("") : "";
    app.innerHTML = `<div class="view">${crumbs([["Атлас", "#/"], [c.name, ""]])}
      <span class="eyebrow">${esc(c.country)}</span><h1>${esc(c.name)}</h1><p class="lede">${esc(c.summary)}</p>
      <div class="twocol">
        <div>${P ? `<figure class="plate"><div class="frame"><img src="${esc(P.image)}" width="${P.width}" height="${P.height}" alt="${esc(P.alt)}"><div class="pins">${cams}</div></div>
          <figcaption>${esc(P.title)} — ${esc(P.credit)}. ${rightsBadge(P)} <a href="${esc(safeUrl(P.object_url))}" target="_blank" rel="noopener">карточка ↗</a>.
          ${P.georef ? `Геопривязка приблизительная: ${esc(P.georef)}.` : "План ещё не геопривязан: места на нём не отмечены."}</figcaption></figure>`
          : `<p class="note">Исторический план этого города ещё не подобран с подтверждёнными правами.</p>`}</div>
        <div><h2>Места</h2><div class="places">${c.places.map((pl) => `<a href="#/place/${esc(pl.id)}"><b>${esc(pl.title)}</b><small>${pl.images.map((i) => esc(i.year_label)).join(" → ")} · ${esc(VERDICT_SHORT(pl))}</small></a>`).join("") || '<p class="note">Места готовятся.</p>'}</div></div>
      </div></div>`;
  }
  const VERDICT_SHORT = (pl) => {
    const best = (pl.pairs || []).map((p) => p.rating);
    if (best.includes("close")) return "есть близкий ракурс";
    if (best.includes("partial")) return "ракурсы частично совпадают";
    if (best.length) return "ракурсы разные";
    return "ракурс не оценён";
  };

  // ---------------- place
  function place(id) {
    let pl = null, c = null;
    for (const city of D.cities) for (const p of city.places) if (p.id === id) { pl = p; c = city; }
    if (!pl) return notFound();
    const imgs = pl.images;
    const cards = imgs.map((img, i) => `<article class="era-card" role="listitem"><span class="yr">${esc(img.year_label)}</span><span class="kind">${esc(KIND[img.kind] || img.kind)}</span>
      ${img.file ? `<img src="${esc(img.file)}" alt="${esc(img.alt || img.title)}" loading="lazy" decoding="async">` : `<p class="note">Изображение не встраивается (права): открыть у хранителя.</p>`}
      <p>${esc(img.title)}</p><p>${esc(img.institution)} · ${rightsBadge(img)}</p>
      ${img.file ? `<button class="pick" data-i="${i}" aria-label="Сравнить: ${esc(img.year_label)}, ${esc(KIND[img.kind] || img.kind)}" style="min-height:44px;border:1px solid #b9ab94;background:#fffdf7">Сравнить</button>` : ""}</article>`).join("");
    const opts = (sel) => imgs.map((img, i) => img.file ? `<option value="${i}" ${i === sel ? "selected" : ""}>${esc(img.year_label)} · ${esc(KIND[img.kind] || img.kind)}</option>` : "").join("");
    const withFile = imgs.map((x, i) => (x.file ? i : -1)).filter((i) => i >= 0);
    const rank = { close: 0, partial: 1, different_viewpoint: 2 };
    const idx = (id) => imgs.findIndex((x) => x.id === id);
    const best = (pl.pairs || []).filter((p) => imgs[idx(p.a)]?.file && imgs[idx(p.b)]?.file)
      .sort((p, q) => rank[p.rating] - rank[q.rating])[0];
    let defA = withFile[0], defB = withFile[withFile.length - 1];
    if (best) { defA = Math.min(idx(best.a), idx(best.b)); defB = Math.max(idx(best.a), idx(best.b)); }
    app.innerHTML = `<div class="view">${crumbs([["Атлас", "#/"], [c.name, `#/city/${c.id}`], [pl.title, ""]])}
      <span class="eyebrow">${esc(c.name)} · одно место — несколько эпох</span><h1>${esc(pl.title)}</h1><p class="lede">${esc(pl.summary)}</p>
      <div class="timeline" role="list" aria-label="Шкала эпох">${cards}</div>
      ${pl.plan_detail ? `<details class="credits" open><summary>Где стояли художник и фотографы — план 1878 года</summary>
        <figure class="plate" style="margin:8px 0"><div class="frame"><img src="${esc(pl.plan_detail.image)}" width="${pl.plan_detail.width}" height="${pl.plan_detail.height}" alt="${esc(pl.plan_detail.alt)}" loading="lazy"><div class="pins">${imgs.map((img) => camMarker(img, pl.plan_detail)).join("")}</div></div>
        <figcaption>${esc(pl.plan_detail.title)} — ${esc(pl.plan_detail.credit)}. ${rightsBadge(pl.plan_detail)} <a href="${esc(safeUrl(pl.plan_detail.object_url))}" target="_blank" rel="noopener">карточка ↗</a>. Точки — оценки по видимым ориентирам и GPS снимков; погрешность привязки плана 30–50 м.</figcaption></figure>
        <div class="legend"><span><b style="background:#7a3f22"></b>литография</span><span><b style="background:#2c5d73"></b>фотография</span><span><b style="background:#5b6b2f"></b>сегодня</span><span>конус — направление взгляда</span></div>
        <div class="camlist" role="group" aria-label="Точки съёмки">${imgs.filter((im) => im.camera && im.camera.px != null).map((im) => `<button type="button" data-img="${esc(im.id)}" ${im.file ? "" : "disabled"}><b class="sw era-${esc(im.era)}"></b>${esc(im.year_label)} · ${esc(KIND[im.kind] || im.kind)} <small>±${esc(im.camera.radius_m)} м · ${Math.round(im.camera.azimuth_deg ?? 0)}°</small></button>`).join("")}</div></details>` : ""}
      <section class="compare" aria-label="Сравнение эпох">
        <div class="ctrls"><label>Тогда <select id="selA">${opts(defA)}</select></label><label>Сейчас <select id="selB">${opts(defB)}</select></label>
          <span role="group" aria-label="Режим"><button data-m="slider" aria-pressed="true">Шторка</button> <button data-m="opacity" aria-pressed="false">Прозрачность</button> <button data-m="sbs" aria-pressed="false">Рядом</button></span>
          <input id="op" type="range" min="0" max="100" value="50" aria-label="Прозрачность верхнего изображения" hidden></div>
        <div id="verdict" class="verdict" role="status"></div>
        <div class="stage" id="stage"><img id="imA" alt=""><div class="top" id="top"><img id="imB" alt=""></div>
          <div class="handle" id="handle" role="slider" tabindex="0" aria-label="Граница между эпохами" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"><span aria-hidden="true">⇆</span></div>
          <span class="tag l" id="tagA"></span><span class="tag r" id="tagB"></span></div>
        <div class="sbs" id="sbs" hidden><img id="sA" alt=""><img id="sB" alt=""></div>
        <p class="note">Изображения не деформируются и не подгоняются друг под друга: шторка показывает два подлинных кадра в одной рамке. Если ракурсы разные, различие видно — это и есть свидетельство.</p>
      </section>
      <section id="threeEpochs" class="cp3" aria-label="Три эпохи одним ползунком"></section>
      <section id="chronoscope" class="chronoscope" aria-label="Любое число эпох и увеличение деталей"></section>
      <section id="curatorialDesk" class="curatorial-desk" aria-label="Архитектура, история, техника и книги"></section>
      ${pl.hunt ? `<section class="hunt" aria-label="Охота за кадром"><svg viewBox="0 0 100 100" width="110" height="110" role="img" aria-label="Компас: направление ${Math.round(pl.hunt.azimuth_deg)}°"><circle cx="50" cy="50" r="46" fill="#faf6ee" stroke="#a8804e"/><text x="50" y="14" text-anchor="middle" font-size="10" fill="#7a3f22">С</text><g transform="rotate(${Number(pl.hunt.azimuth_deg) || 0} 50 50)"><path d="M50 50 L44 18 L50 8 L56 18 Z" fill="#7a3f22"/></g><circle cx="50" cy="50" r="4" fill="#22362f"/></svg>
        <div><span class="eyebrow">Охота за кадром</span><h3 style="margin:4px 0">${esc(pl.hunt.title || "Встаньте туда, где стоял художник")}</h3><p style="font:14px/1.55 system-ui;margin:0">${esc(pl.hunt.instructions)}</p>
        <p style="font:12px system-ui;color:#6f6f63">Координаты (оценка, ±${esc(pl.hunt.radius_m)} м): ${Number(pl.hunt.lat).toFixed(5)}, ${Number(pl.hunt.lon).toFixed(5)} · направление ${Math.round(pl.hunt.azimuth_deg)}°. Ваше фото остаётся на вашем устройстве; мы ничего не загружаем.</p></div></section>` : ""}
      ${pl.story ? `<section class="story"><span class="eyebrow">История места</span>${pl.story}</section>` : ""}
      <details class="credits"><summary>Источники и права (${imgs.length})</summary>${imgs.map((img) => `<h3 style="font-size:17px;margin:12px 0 2px">${esc(img.year_label)} · ${esc(KIND[img.kind] || img.kind)}</h3>${credits(img)}`).join("")}</details>
    </div>`;
    setupCompare(pl);
    if (window.CityOnPaperThreeEpochs) window.CityOnPaperThreeEpochs.mount(document.getElementById("threeEpochs"), pl.images);
    if (window.CityOnPaperChronoscope) window.CityOnPaperChronoscope.mount(document.getElementById("chronoscope"), pl.images);
    if (window.CityOnPaperCuratorialDesk) window.CityOnPaperCuratorialDesk.mount(document.getElementById("curatorialDesk"), pl.id);
  }

  function setupCompare(pl) {
    const $ = (id) => document.getElementById(id);
    let mode = "slider", split = 50;
    const pair = (a, b) => (pl.pairs || []).find((p) => (p.a === a && p.b === b) || (p.a === b && p.b === a));
    function render() {
      const a = +$("selA").value, b = +$("selB").value, A = pl.images[a], B = pl.images[b];
      for (const [im, s] of [[$("imA"), A], [$("sA"), A], [$("imB"), B], [$("sB"), B]]) { im.src = s.file; im.alt = `${s.year_label}: ${s.alt || s.title}`; }
      const tag = (x) => x.year_label + (x.id.startsWith("derived-") ? " · фрагмент 360°-панорамы (производная)" : "");
      $("tagA").textContent = tag(A); $("tagB").textContent = tag(B);
      const p = pair(A.id, B.id);
      const r = p ? p.rating : "unknown";
      const opBtn = document.querySelector('.ctrls [data-m="opacity"]');
      opBtn.disabled = r !== "close";
      opBtn.title = r === "close" ? "" : "Наложение с прозрачностью доступно только для близких ракурсов: иначе оно создаёт ложное впечатление совмещения";
      if (mode === "opacity" && r !== "close") mode = "slider";
      const v = $("verdict");
      v.className = "verdict " + r;
      v.innerHTML = `<strong>${esc({ close: "Близкий ракурс", partial: "Частичное совпадение", different_viewpoint: "Разные точки съёмки", unknown: "Не оценено" }[r])}</strong> — ${esc(VERDICT[r])}${p && p.reason ? `<br>${esc(p.reason)}` : ""}${p && p.by ? `<br><small>Оценил: ${esc(p.by)}. Ручная оценка, не автоматическое совмещение.</small>` : ""}`;
      $("stage").hidden = mode === "sbs"; $("sbs").hidden = mode !== "sbs"; $("op").hidden = mode !== "opacity"; $("handle").hidden = mode !== "slider";
      $("top").style.clipPath = mode === "slider" ? `inset(0 0 0 ${split}%)` : "none";
      $("top").style.opacity = mode === "opacity" ? $("op").value / 100 : 1;
      $("handle").style.left = split + "%"; $("handle").setAttribute("aria-valuenow", Math.round(split));
      document.querySelectorAll(".ctrls [data-m]").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.m === mode)));
    }
    $("selA").onchange = $("selB").onchange = $("op").oninput = render;
    document.querySelectorAll(".ctrls [data-m]").forEach((x) => (x.onclick = () => { mode = x.dataset.m; render(); }));
    document.querySelectorAll(".pick").forEach((x) => (x.onclick = () => {
      const i = x.dataset.i;
      if (!pl.images[i].file) return;
      $("selA").value = i; render(); $("stage").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
    }));
    document.querySelectorAll(".camlist [data-img]").forEach((x) => (x.onclick = () => {
      const i = pl.images.findIndex((im) => im.id === x.dataset.img);
      if (i < 0 || !pl.images[i].file) return;
      $("selA").value = String(i); render(); $("stage").scrollIntoView({ block: "center" });
    }));
    const st = $("stage");
    const setX = (x) => { const r = st.getBoundingClientRect(); split = Math.max(0, Math.min(100, (x - r.left) / r.width * 100)); render(); };
    st.addEventListener("pointerdown", (e) => { if (mode !== "slider") return; st.setPointerCapture(e.pointerId); setX(e.clientX); });
    st.addEventListener("pointermove", (e) => { if (mode === "slider" && st.hasPointerCapture(e.pointerId)) setX(e.clientX); });
    $("handle").addEventListener("keydown", (e) => {
      const k = { ArrowLeft: -2, ArrowRight: 2, PageDown: -10, PageUp: 10 }[e.key];
      if (k) split = Math.max(0, Math.min(100, split + k)); else if (e.key === "Home") split = 0; else if (e.key === "End") split = 100; else return;
      e.preventDefault(); render();
    });
    render();
  }

  function notFound() { app.innerHTML = `<p class="note">Не найдено. <a href="#/">Вернуться к атласу</a></p>`; }

  function route() {
    if (!D) return;
    const h = location.hash.replace(/^#\/?/, "").split("/");
    if (h[0] === "city") {
      const ac = window.Atlas && Atlas.data ? Atlas.data.cities.find((x) => x.id === h[1]) : null;
      if (ac && ac.featured && D.cities.some((x) => x.id === ac.featured)) { city(ac.featured); Atlas.city(app, ac.id, true); }
      else if (ac) Atlas.city(app, ac.id);
      else city(h[1]);
    } else if (h[0] === "place") place(h[1]);
    else if (window.Atlas && Atlas.data) Atlas.portal(app);
    else portal();
    if (location.hash && location.hash !== "#/") app.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  Promise.all([fetch("data/eras.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
    window.Atlas ? Atlas.load().catch(() => null) : null])
    .then(([d]) => { D = d; route(); })
    .catch((e) => { app.innerHTML = `<p class="note">Не удалось загрузить данные атласа (${esc(e.message)}). Откройте страницу через HTTP-сервер.</p>`; });
  addEventListener("hashchange", route);
  addEventListener("error", (e) => { if (e.target && e.target.tagName === "IMG") e.target.alt = "Изображение не загрузилось: " + (e.target.alt || ""); }, true);
})();
