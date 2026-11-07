/* Атлас эпох v2: все города Европы и места Бенуа (Issue #34).
 * Данные: data/atlas.json (города, координаты, метки на карте 1769 г., работы Бенуа)
 * + опубликованные кураторские файлы музея (../data/curation/*.json), сгруппированные по названию города.
 * Исторические изображения показываются без изменений (object-fit: contain, без фильтров). */
"use strict";
window.Atlas = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safe = (u) => (/^https:\/\//.test(u || "") || /^(img|\.\.\/assets)\//.test(u || "") ? u : "#");
  const CURATION = ["../data/curation/world-graphic-archive-v1.json", "../data/curation/museum-expansion-v1.json",
    "../data/curation/cc0-gallery-20261103.json", "../data/curation/benoist-paris-musees-v1.json"];
  const RIGHTS = { cc0: "CC0", public_domain_commons: "общественное достояние (Commons)", cc_by: "CC BY", cc_by_sa: "CC BY-SA" };
  let A = null, W = null, filter = { q: "", group: "all" }, zoom = 1;

  const load = () => A ? Promise.resolve(A) : fetch("data/atlas.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }).then((d) => (A = d));
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
    const pins = A.cities.filter((c) => c.xy).map((c) =>
      `<a class="dot ${c.featured ? "featured" : c.benoist ? "benoist" : "other"}" href="#/city/${esc(c.id)}" tabindex="-1" aria-hidden="true"
        data-id="${esc(c.id)}" style="left:${c.xy[0] / P.width * 100}%;top:${c.xy[1] / P.height * 100}%"><i></i><span>${esc(c.name)}</span></a>`).join("");
    const groups = [["all", "Все города"], ["benoist", "Города Бенуа"], ["featured", "С историями эпох"], ...A.regions.map((r) => [`r:${r}`, r])];
    app.innerHTML = `<div class="view">
      <span class="eyebrow">Атлас эпох · вход через старую карту</span>
      <h1>Города на бумаге:<br>от Бретани до Вильнюса</h1>
      <p class="lede">${A.cities.length} городов и мест Европы; ${A.counts.benoist_places} из них рисовали Феликс и Филипп Бенуа. Метки стоят на подлинной карте Европы XVIII века — она красива, но неточна, поэтому положение меток приблизительное. Внутри города — работы из музеев и библиотек с источниками и правами.</p>
      <div class="tools" role="search"><label class="sr" for="q">Поиск города</label>
        <input id="q" type="search" placeholder="Город, страна или регион" value="${esc(filter.q)}" autocomplete="off">
        <select id="grp" aria-label="Показать">${groups.map(([v, l]) => `<option value="${esc(v)}" ${filter.group === v ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></div>
      <figure class="plate"><div class="zoombar"><button type="button" id="zin" aria-label="Увеличить карту">+</button><button type="button" id="zout" aria-label="Уменьшить карту">−</button><span>Карта Европы 1769 г. · <b class="sw benoist"></b> Бенуа <b class="sw featured"></b> истории эпох <b class="sw other"></b> другие города</span></div>
        <div class="mapwrap" id="mapwrap"><div class="frame" id="frame" style="width:${zoom * 100}%"><img src="${esc(P.image)}" ${P.image_small ? `srcset="${esc(P.image_small)} 1000w, ${esc(P.image)} 2000w" sizes="(max-width: 700px) ${Math.round(zoom * 100)}vw, ${Math.round(zoom * 1400)}px"` : ""} width="${P.width}" height="${P.height}" alt="${esc(P.alt)}" fetchpriority="high"><div class="pins">${pins}</div></div></div>
        <figcaption>${esc(P.title)} — ${esc(P.credit)}. <a href="${esc(safe(P.object_url))}" target="_blank" rel="noopener">карточка ↗</a>. ${esc(A.portal_note)}</figcaption></figure>
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
    const setZoom = (z) => {
      zoom = Math.max(1, Math.min(4, z));
      document.getElementById("frame").style.width = `${zoom * 100}%`;
    };
    document.getElementById("zin").onclick = () => setZoom(zoom * 1.6);
    document.getElementById("zout").onclick = () => setZoom(zoom / 1.6);
    draw();
    works().then(draw);
  }

  // Commons originals can be many MB: use the official 640 px thumbnail of the same file (no other change).
  const thumb = (u) => {
    const m = /^https:\/\/upload\.wikimedia\.org\/wikipedia\/commons\/([0-9a-f])\/([0-9a-f]{2})\/([^?#/]+)/.exec(u || "");
    if (!m || /\.(svg|tiff?)$/i.test(m[3])) return u;
    return `https://upload.wikimedia.org/wikipedia/commons/thumb/${m[1]}/${m[2]}/${m[3]}/640px-${m[3]}`;
  };
  // ---------- city (generic, for every city)
  const card = (w) => `<article class="wcard">
      ${w.image ? `<a href="${esc(safe(w.url))}" target="_blank" rel="noopener"><img src="${esc(safe(thumb(w.image)))}" alt="${esc((w.medium ? w.medium + ": " : "") + (w.title || w.name))}" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.outerHTML='<span class=&quot;noimg&quot;>Изображение сейчас не загрузилось — откройте источник</span>'"></a>`
        : `<div class="noimg">Изображение не встраивается: права хранителя. <a href="${esc(safe(w.url))}" target="_blank" rel="noopener">Открыть у хранителя ↗</a></div>`}
      <h4>${esc(w.title || w.name)}</h4>
      <p>${esc(w.artist || w.maker || "")}${w.date ? " · " + esc(w.date) : ""}</p>
      <p class="src">${esc(w.institution || w.source || "")} · <span class="rights ${w.rights_class === "link" ? "link" : "open"}">${esc(w.rights_label || RIGHTS[w.rights] || w.rights || "")}</span> · <a href="${esc(safe(w.url))}" target="_blank" rel="noopener">источник ↗</a></p>
    </article>`;

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
      ${c.albums && c.albums.length ? `<p class="note">Альбомы и серии: ${c.albums.map(esc).join("; ")}.</p>` : ""}
      ${(c.works || []).length ? `<h2>Бенуа: ${c.works.length}</h2><div class="wgrid">${c.works.map(card).join("")}</div>` : ""}
      <h2 id="others">Другие виды из музеев</h2><div class="wgrid" id="wg"><p class="note">Загружаем…</p></div>
      <button type="button" id="more" class="morebtn" hidden>Показать ещё</button>
      <section class="hunt2"><span class="eyebrow">Найти больше</span><p>Поиск в открытых архивах (откроется у хранителя; права проверяйте в карточке):</p>
        <p>${search.map(([n, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(n)} ↗</a>`).join(" · ")}</p></section>`;
    if (append) app.querySelector(".view").insertAdjacentHTML("beforeend", `<hr class="sep">${body}`);
    else app.innerHTML = `<div class="view">${head}${body}</div>`;
    let n = 24;
    works().then((Wm) => {
      const list = Wm.get(c.name) || [];
      const draw = () => {
        document.getElementById("wg").innerHTML = list.length
          ? list.slice(0, n).map((w) => card({ ...w, title: w.title_original || w.name, artist: w.maker, institution: w.source })).join("")
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
