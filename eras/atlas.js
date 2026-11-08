/* Атлас эпох v2: все города Европы и места Бенуа (Issue #34).
 * Данные: data/atlas.json (города, координаты, метки на карте 1769 г., работы Бенуа)
 * + опубликованные кураторские файлы музея (../data/curation/*.json), сгруппированные по названию города.
 * Исторические изображения показываются без изменений (object-fit: contain, без фильтров). */
"use strict";
window.Atlas = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safe = (u) => (/^https:\/\//.test(u || "") || /^(img|thumbs|\.\.\/assets)\//.test(u || "") ? u : "#");
  const safeLink = (u) => (/^https?:\/\//.test(u || "") ? u : "#"); // holder pages; some institutions are http-only
  const CURATION = ["../data/curation/world-graphic-archive-v1.json", "../data/curation/museum-expansion-v1.json",
    "../data/curation/cc0-gallery-20261103.json", "../data/curation/benoist-paris-musees-v1.json"];
  const RIGHTS = { cc0: "CC0", public_domain_commons: "общественное достояние (Commons)", cc_by: "CC BY", cc_by_sa: "CC BY-SA" };
  let A = null, W = null, T = {}, filter = { q: "", group: "all" };

  const load = () => A ? Promise.resolve(A) : Promise.all([
    fetch("data/atlas.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }),
    fetch("data/thumbs.json").then((r) => (r.ok ? r.json() : {})).catch(() => ({})),
  ]).then(([d, t]) => { T = t; return (A = d); });
  function works() {
    if (W) return Promise.resolve(W);
    return Promise.all(CURATION.map((u) => fetch(u).then((r) => (r.ok ? r.json() : { items: [] })).catch(() => ({ items: [] }))))
      .then((all) => {
        W = new Map();
        const seen = new Set();
        for (const d of all) for (const it of d.items || []) {
          if (!it.city || !it.image || !/^https:\/\//.test(it.url || "") || seen.has(it.url)) continue;
          seen.add(it.url);
          if (!W.has(it.city)) W.set(it.city, []);
          W.get(it.city).push(it);
        }
        return W;
      });
  }
  const count = (c) => (W && W.get(c.name) ? W.get(c.name).length : 0) + (c.works || []).length;

  // ---------- portal
  function portal(app) {
    const P = A.portal;
    const groups = [["all", "Все города"], ["benoist", "Города Бенуа"], ["featured", "С историями эпох"], ...A.regions.map((r) => [`r:${r}`, r])];
    app.innerHTML = `<div class="view">
      <span class="eyebrow">Атлас эпох · вход через старую карту</span>
      <h1>Города на бумаге:<br>от Бретани до Вильнюса</h1>
      <p class="lede">${A.cities.length} городов и мест — в основном Европа; ${A.counts.benoist_places} из них рисовали Феликс и Филипп Бенуа (${A.counts.benoist_works} работ в музеях и библиотеках). Метки стоят на подлинной карте Европы XVIII века — она красива, но неточна, поэтому положение меток приблизительное. Внутри города — работы из музеев и библиотек с источниками и правами.</p>
      <div class="tools" role="search"><label class="sr" for="q">Поиск города</label>
        <input id="q" type="search" placeholder="Город, страна или регион" value="${esc(filter.q)}" autocomplete="off">
        <select id="grp" aria-label="Показать">${groups.map(([v, l]) => `<option value="${esc(v)}" ${filter.group === v ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></div>
      <figure class="plate"><div id="maphost"></div>
        <figcaption><span class="legend2"><b class="sw benoist"></b> города Бенуа <b class="sw featured"></b> истории эпох <b class="sw other"></b> другие города · приближайте кнопками «+ / −» в углу или двумя пальцами</span><br>${esc(P.title)} — ${esc(P.credit)}. <a href="${esc(safe(P.object_url))}" target="_blank" rel="noopener">карточка ↗</a>. ${esc(A.portal_note)}</figcaption></figure>
      <p class="note" id="shown" role="status" aria-live="polite"></p>
      <div class="citylist" id="list"></div></div>`;
    const q = document.getElementById("q"), grp = document.getElementById("grp");
    const draw = () => {
      const t = filter.q.trim().toLowerCase();
      const rows = A.cities.filter((c) => {
        if (filter.group === "benoist" && !c.benoist) return false;
        if (filter.group === "featured" && !c.featured) return false;
        if (filter.group.startsWith("r:") && c.country !== filter.group.slice(2)) return false;
        return !t || [c.name, c.name_orig, c.country, c.area].some((x) => (x || "").toLowerCase().includes(t));
      }).sort((a, b) => (b.featured ? 1 : 0) - (a.featured ? 1 : 0) || (b.works || []).length - (a.works || []).length || count(b) - count(a) || a.name.localeCompare(b.name, "ru"));
      const ids = new Set(rows.map((c) => c.id));
      document.querySelectorAll(".dot").forEach((d) => d.classList.toggle("dim", !ids.has(d.dataset.id)));
      document.getElementById("shown").textContent = `Показано городов: ${rows.length} из ${A.cities.length}.`;
      document.getElementById("list").innerHTML = rows.map((c) => `<a class="ccard" href="#/city/${esc(c.id)}"><b>${esc(c.name)}</b>
        <small>${esc(c.country)}${c.area ? " · " + esc(c.area) : ""}</small>
        <span>${c.featured ? '<em class="badge f">истории эпох</em>' : ""}${c.benoist ? `<em class="badge b">Бенуа · ${(c.works || []).length}</em>` : ""}<em class="badge">${count(c) ? `${count(c)} работ` : "ищем материалы"}</em></span></a>`).join("") || '<p class="note">Ничего не найдено.</p>';
    };
    q.addEventListener("input", () => { filter.q = q.value; draw(); });
    grp.addEventListener("change", () => { filter.group = grp.value; draw(); });
    window.Maps && Maps.portal(document.getElementById("maphost"), A, () => draw());
    draw();
    works().then(draw);
  }

  // Commons: prefer our self-hosted copy of Wikimedia's own 500 px thumbnail (data/thumbs.json), else the standard
  // 500 px thumbnail on thumb.wikimedia.org. Pixels are Wikimedia's downscale of the same file: no crop, no colour change.
  const commonsName = (u) => {
    const m = /^https:\/\/(?:upload|thumb)\.wikimedia\.org\/wikipedia\/commons\/(?:thumb\/)?([0-9a-f])\/([0-9a-f]{2})\/([^?#/]+)/.exec(u || "");
    return m ? [m[1], m[2], m[3]] : null;
  };
  const remoteThumb = (u) => {
    const m = commonsName(u);
    if (!m || /\.(svg|tiff?|pdf|djvu)$/i.test(m[2])) return u;
    return `https://thumb.wikimedia.org/wikipedia/commons/thumb/${m[0]}/${m[1]}/${m[2]}/500px-${m[2]}`;
  };
  const thumb = (u) => {
    const m = commonsName(u);
    if (m) { let n; try { n = decodeURIComponent(m[2]).replace(/_/g, " "); } catch (e) { n = ""; }
      const local = T[n] || T[n.replace(/ /g, "_")]; if (local) return local; }
    return remoteThumb(u);
  };
  // one retry from the remote thumbnail host, then a calm placeholder with the source link
  window.__imgErr = (img) => {
    const alt = img.dataset.remote;
    if (alt && img.src !== alt && !img.dataset.tried) { img.dataset.tried = "1"; img.src = alt; return; }
    const s = document.createElement("span"); s.className = "noimg"; s.textContent = "Изображение сейчас не загрузилось — откройте источник";
    img.replaceWith(s);
  };
  const imgTag = (u, alt) => `<img src="${esc(safe(thumb(u)))}" data-remote="${esc(safe(remoteThumb(u)))}" alt="${esc(alt)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="__imgErr(this)">`;
  // ---------- city (generic, for every city)
  const card = (w) => `<article class="wcard"${w.wid ? ` id="w-${esc(w.wid)}"` : ""}>
      ${w.image ? `<a href="${esc(safeLink(w.url))}" target="_blank" rel="noopener">${imgTag(w.image, (w.medium ? w.medium + ": " : "") + (w.title || w.name))}</a>`
        : `<div class="noimg">Изображение не встраивается: права хранителя. <a href="${esc(safeLink(w.url))}" target="_blank" rel="noopener">Открыть у хранителя ↗</a></div>`}
      <h4>${esc(w.title || w.name)}</h4>
      <p>${esc(w.artist || w.maker || "")}${w.date ? " · " + esc(w.date) : ""}</p>
      <p class="src">${esc(w.institution || w.source || "")} · <span class="rights ${w.rights_class === "link" ? "link" : "open"}">${esc(w.rights_label || RIGHTS[w.rights] || w.rights || "")}</span> · <a href="${esc(safeLink(w.url))}" target="_blank" rel="noopener">источник ↗</a></p>
    </article>`;

  // ---------- "одно место — разные эпохи": all works of one depicted site + the same place today, swipe compare
  const yearOf = (d) => { const m = /(1[5-9]\d\d|20\d\d)/.exec(d || ""); return m ? +m[1] : null; };
  function epochs(c, sites) {
    const byW = new Map(sites.map((x) => [x.wid, x]));
    const frames = (g) => {
      const fs = g.works.map((w) => byW.get(w)).filter((x) => x && x.image).map((x) => ({
        img: x.image, year: yearOf(x.date) || yearOf(x.title), label: x.title, url: x.url, credit: "", kind: "then" }))
        .sort((a, b) => (a.year || 1850) - (b.year || 1850));
      if (g.today) fs.push({ img: g.today.image, year: yearOf(g.today.date) || "сегодня", label: `Сегодня: ${g.name}`, url: g.today.page,
        credit: `Фото: ${g.today.author || "автор на Commons"}`, lic: g.today.license, licUrl: g.today.license_url, kind: "now" });
      return fs;
    };
    const groups = c.epochs.map((g) => ({ ...g, frames: frames(g) })).filter((g) => g.frames.length >= 2);
    const list = document.getElementById("eplist");
    if (!groups.length) { document.querySelector(".epochs").hidden = true; return; }
    list.innerHTML = `<div class="epchips" role="tablist" aria-label="Места">${groups.map((g, i) =>
      `<button type="button" role="tab" data-i="${i}" aria-selected="${i === 0}">${esc(g.name ? g.name.charAt(0).toUpperCase() + g.name.slice(1) : "")} <small>${g.frames.length}</small></button>`).join("")}</div>`;
    const view = document.getElementById("epview");
    const show = (gi) => {
      const g = groups[gi];
      list.querySelectorAll("button").forEach((b) => b.setAttribute("aria-selected", String(+b.dataset.i === gi)));
      const lab = (f) => `${f.year || "год не указан"}${f.kind === "now" ? " · сегодня" : ""}`;
      const opt = (sel) => g.frames.map((f, i) => `<option value="${i}" ${i === sel ? "selected" : ""}>${esc(lab(f))} — ${esc((f.label || "").slice(0, 60))}</option>`).join("");
      let a = 0, b = g.frames.length - 1;
      view.innerHTML = `<div class="eptrack">${g.frames.map((f, i) => `<button type="button" class="epf ${f.kind}" data-f="${i}" aria-label="${esc(lab(f))}: ${esc(f.label)}">
          ${imgTag(f.img, f.label || g.name)}<b>${esc(lab(f))}</b></button>`).join("")}</div>
        <div class="epcmp"><div class="ctrls"><label>Было <select id="epA">${opt(a)}</select></label><label>Стало <select id="epB">${opt(b)}</select></label></div>
          <div class="epstage" id="epstage"><img id="epImB" alt=""><div class="epTop" id="epTop"><img id="epImA" alt=""></div>
            <div class="eph" id="epH2" role="slider" tabindex="0" aria-label="Граница сравнения" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"><span>⇆</span></div>
            <span class="tag l" id="epTagA"></span><span class="tag r" id="epTagB"></span></div>
          <p class="mapnote" id="epCredit"></p></div>`;
      const st = document.getElementById("epstage"), top = document.getElementById("epTop"), h = document.getElementById("epH2");
      const setPos = (p) => { p = Math.max(0, Math.min(100, p)); top.style.clipPath = `inset(0 ${100 - p}% 0 0)`; h.style.left = p + "%"; h.setAttribute("aria-valuenow", String(Math.round(p))); };
      const upd = () => {
        const A = g.frames[a], B = g.frames[b];
        const ia = document.getElementById("epImA"), ib = document.getElementById("epImB");
        ia.src = safe(thumb(A.img)); ia.alt = `Было: ${lab(A)} — ${A.label}`; ib.src = safe(thumb(B.img)); ib.alt = `Стало: ${lab(B)} — ${B.label}`;
        document.getElementById("epTagA").textContent = lab(A); document.getElementById("epTagB").textContent = lab(B);
        document.getElementById("epCredit").innerHTML = [A, B].map((f) => `<a href="${esc(safeLink(f.url))}" target="_blank" rel="noopener">${esc(lab(f))}: источник ↗</a>${f.credit ? " · " + esc(f.credit) : ""}${f.lic ? `, ${/^https?:\/\//.test(f.licUrl || "") ? `<a href="${esc(f.licUrl)}" target="_blank" rel="noopener">${esc(f.lic)}</a>` : esc(f.lic)}` : ""}`).join(" · ");
        view.querySelectorAll(".epf").forEach((x) => x.classList.toggle("on", +x.dataset.f === a || +x.dataset.f === b));
      };
      document.getElementById("epA").onchange = (e) => { a = +e.target.value; upd(); };
      document.getElementById("epB").onchange = (e) => { b = +e.target.value; upd(); };
      view.querySelectorAll(".epf").forEach((x) => (x.onclick = () => { const i = +x.dataset.f; if (i === a || i === b) return; if (i < b) a = i; else b = i;
        document.getElementById("epA").value = a; document.getElementById("epB").value = b; upd(); st.scrollIntoView({ behavior: "smooth", block: "nearest" }); }));
      const move = (e) => { const r = st.getBoundingClientRect(); setPos((e.clientX - r.left) / r.width * 100); };
      st.addEventListener("pointerdown", (e) => { st.setPointerCapture(e.pointerId); move(e); st.onpointermove = move; });
      st.addEventListener("pointerup", () => (st.onpointermove = null));
      h.addEventListener("keydown", (e) => { const v = +h.getAttribute("aria-valuenow"); if (e.key === "ArrowLeft") setPos(v - 5); else if (e.key === "ArrowRight") setPos(v + 5); else if (e.key === "Home") setPos(0); else if (e.key === "End") setPos(100); else return; e.preventDefault(); });
      setPos(50); upd();
    };
    list.querySelectorAll("button").forEach((x) => (x.onclick = () => show(+x.dataset.i)));
    show(0);
  }

  function city(app, id, append) {
    const c = A.cities.find((x) => x.id === id);
    if (!c) return false;
    const enc = encodeURIComponent;
    const search = [
      ["Library of Congress", `https://www.loc.gov/pictures/search/?q=${enc((c.name_orig || c.name) + " lithograph")}`],
      ["Europeana", `https://www.europeana.eu/ru/search?query=${enc(c.name_orig || c.name)}&qf=TYPE%3A%22IMAGE%22`],
      ["Gallica", `https://gallica.bnf.fr/services/engine/search/sru?query=gallica%20all%20%22${enc(c.name_orig || c.name)}%22%20and%20dc.type%20all%20%22image%22`],
      ["Wikimedia Commons", `https://commons.wikimedia.org/w/index.php?search=${enc((c.name_orig || c.name) + " lithograph")}&title=Special:MediaSearch&type=image`],
    ];
    const head = `<nav class="crumbs" aria-label="Путь"><a href="#/">Атлас</a> › <span aria-current="page">${esc(c.name)}</span></nav>
      <span class="eyebrow">${esc(c.country)}${c.area ? " · " + esc(c.area) : ""}</span>
      <h1>${esc(c.name)}${c.name_orig && c.name_orig !== c.name ? ` <small class="orig">${esc(c.name_orig)}</small>` : ""}</h1>`;
    const body = `<p class="coords">${Number(c.lat).toFixed(4)}, ${Number(c.lon).toFixed(4)} · <a href="https://www.openstreetmap.org/?mlat=${c.lat}&mlon=${c.lon}#map=15/${c.lat}/${c.lon}" target="_blank" rel="noopener">город сегодня на карте OSM ↗</a></p>
      <section class="cmap" aria-labelledby="cmapH"><h2 id="cmapH">Карта города${c.plan ? ": тогда и сейчас" : ""}</h2><div id="cmaphost"></div></section>
      ${(c.epochs || []).length ? `<section class="epochs" aria-labelledby="epH"><h2 id="epH">Одно место — разные эпохи</h2>
        <p class="lede">Как было и как есть: листы XIX века и снимок того же места сегодня. Точки съёмки обычно не совпадают — это сопоставление, а не наложение; изображения не искажаются.</p>
        <div id="eplist"></div><div id="epview"></div></section>` : ""}
      ${c.albums && c.albums.length ? `<p class="note">Альбомы и серии: ${c.albums.map(esc).join("; ")}.</p>` : ""}
      ${(c.works || []).length ? `<h2>Бенуа: ${c.works.length}</h2><div class="wgrid">${c.works.map(card).join("")}</div>` : ""}
      <h2 id="others">Другие виды из музеев</h2><div class="wgrid" id="wg"><p class="note">Загружаем…</p></div>
      <button type="button" id="more" class="morebtn" hidden>Показать ещё</button>
      ${(c.halls || []).length ? `<section class="halls"><span class="eyebrow">Этот город в других залах музея</span><p>${c.halls.map(([u, t]) => `<a href="${esc(/^\.\.\/[a-z]/.test(u) ? u : "#")}">${esc(t)} →</a>`).join("")}</p></section>` : ""}
      <section class="hunt2"><span class="eyebrow">Найти больше</span><p>Поиск в открытых архивах (откроется у хранителя; права проверяйте в карточке):</p>
        <p>${search.map(([n, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(n)} ↗</a>`).join(" · ")}</p></section>`;
    if (append) app.querySelector(".view").insertAdjacentHTML("beforeend", `<hr class="sep">${body}`);
    else app.innerHTML = `<div class="view">${head}${body}</div>`;
    const sites = c.sites || [];
    const siteBy = new Map(sites.map((x) => [x.url, x]));
    if (window.Maps) try { Maps.city(document.getElementById("cmaphost"), c, sites, thumb); } catch (e) { /* map optional */ }
    document.getElementById("cmaphost").addEventListener("click", (e) => {
      const a = e.target.closest("a[data-w]"); if (!a) return;
      e.preventDefault(); const t = document.getElementById("w-" + a.dataset.w);
      if (t) { t.scrollIntoView({ behavior: "smooth", block: "center" }); t.classList.add("flash"); setTimeout(() => t.classList.remove("flash"), 1600); }
    });
    if ((c.epochs || []).length) epochs(c, sites);
    let n = 24;
    works().then((Wm) => {
      const list = Wm.get(c.name) || [];
      const draw = () => {
        document.getElementById("wg").innerHTML = list.length
          ? list.slice(0, n).map((w) => card({ ...w, title: w.title_original || w.name, artist: w.maker, institution: w.source, wid: (siteBy.get(w.url) || {}).wid })).join("")
          : '<p class="note">Пока нет проверенных работ из открытых музейных собраний. Город в очереди на исследование.</p>';
        const m = document.getElementById("more");
        m.hidden = list.length <= n;
        m.textContent = `Показать ещё (${list.length - n})`;
        m.onclick = () => { n += 24; draw(); };
      };
      draw();
    });
    return true;
  }
  return { load, portal, city, works, get data() { return A; } };
})();
