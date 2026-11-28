/* Книга видов: один хребет сайта. Всё строится из реальных данных атласа (eras/data/atlas.json). */
(() => {
  "use strict";
  const $app = document.getElementById("book");
  const $crumbs = document.getElementById("crumbs");
  const E = "../eras/";
  const SEEN_KEY = "cop-book-seen-v1";

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const up = (u) => String(u || "").replace(/^http:\/\//i, "https://");
  const safe = (u0) => { const u = up(u0); return (/^https:\/\//.test(u || "") || /^(\.\.?\/|[a-z0-9_\-/]+\.[a-z0-9]+$)/i.test(u || "") ? u : ""); };
  const plural = (n, a, b, c) => { const m = n % 100, k = n % 10; return n + " " + (m > 10 && m < 20 ? c : k === 1 ? a : k > 1 && k < 5 ? b : c); };
  const seenSet = () => { try { return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]")); } catch (e) { return new Set(); } };
  const markSeen = (id) => { try { const s = seenSet(); s.add(id); localStorage.setItem(SEEN_KEY, JSON.stringify([...s])); } catch (e) { /* private mode */ } };

  let D = null; // model

  // ---------- images: our own 500 px copy first, then Wikimedia's own downscale; one calm fallback
  let T = {};
  const commonsName = (u) => { const m = /^https:\/\/(?:upload|thumb)\.wikimedia\.org\/wikipedia\/commons\/(?:thumb\/)?([0-9a-f])\/([0-9a-f]{2})\/([^?#/]+)/.exec(u || ""); return m ? [m[1], m[2], m[3]] : null; };
  const remote = (u, px) => { const m = commonsName(u); if (!m || /\.(svg|tiff?|pdf|djvu)$/i.test(m[2])) return u; return `https://thumb.wikimedia.org/wikipedia/commons/thumb/${m[0]}/${m[1]}/${m[2]}/${px || 500}px-${m[2]}`; };
  const local = (u) => {
    if (u && T[u]) return E + T[u];
    const m = commonsName(u); if (!m) return "";
    let n = ""; try { n = decodeURIComponent(m[2]).replace(/_/g, " "); } catch (e) { /* keep empty */ }
    const t = T[n] || T[n.replace(/ /g, "_")]; return t ? E + t : "";
  };
  window.__bkImg = (img) => {
    const alt = img.dataset.remote;
    if (alt && img.src !== alt && !img.dataset.tried) { img.dataset.tried = "1"; img.src = alt; return; }
    const s = document.createElement("span"); s.className = img.className + " ph"; s.setAttribute("role", "img"); s.setAttribute("aria-label", "Изображение не загрузилось");
    img.replaceWith(s);
  };
  const img = (u, alt, cls, px) => {
    const first = local(u) || remote(u, px || 500);
    return `<img class="${cls || ""}" src="${esc(safe(first))}" data-remote="${esc(safe(remote(u, px || 500)))}" alt="${esc(alt)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="__bkImg(this)">`;
  };

  // ---------- titles: Commons file names are long; show the short human name
  const clean = (t) => String(t || "").replace(/\.(jpe?g|png|tiff?)$/i, "").replace(/_/g, " ")
    .replace(/\s*[-–]\s*(estampe|gravure|lithographie|btv\w+|gallica).*$/i, "")
    .replace(/\s*\(([^)]*(n°|no\.|inv|cote|btv|De Vinck)[^)]*)\)/gi, "").replace(/\s+/g, " ").trim();
  const cut = (t, n) => (t.length > n ? t.slice(0, n - 1).replace(/[\s,;:.\-–(]+\S*$/, "") + "…" : t);
  // Some atlas records are modern snapshots (geograph, phone photos), not prints: keep them out of a book of old views.
  const modernPhoto = (t) => /geograph|\bIMG_|\bDSC_?\d|panoramio|flickr|City of London School|\bsundial\b|\bcourtyard\b|war memorial/i.test(String(t || ""));
  // Where the original is kept, read from catalogue identifiers that are part of the record itself (never guessed).
  const holder = (t, u) => {
    t = String(t || "");
    if (/\bRP-[PT]-/.test(t)) return "Рейксмюзеум, Амстердам";
    if (/\bMET\s?DP\d/.test(t) || /metmuseum\.org/.test(u || "")) return "Метрополитен-музей, Нью-Йорк";
    if (/\bBM\s?\d{4},/.test(t)) return "Британский музей, Лондон";
    if (/btv1b/i.test(t) || /gallica\.bnf\.fr/.test(u || "")) return "Национальная библиотека Франции (Галлика)";
    if (/\bWGA\d/.test(t)) return "Web Gallery of Art";
    if (/loc\.gov/.test(u || "")) return "Библиотека Конгресса США";
    return "";
  };
  // the line a printer set under a lithograph: who drew it, where it was made / kept
  const imprint = (p) => {
    const first = (p.artist || "").split(";")[0].replace(/\s*\(.*$/, "").trim();
    const printer = (p.artist || "").split(";").map((x) => x.trim()).find((x) => /типограф|печат/i.test(x));
    return { left: first ? "Рисовал: " + first : "Автор: в записи хранителя", right: printer ? "Печатал: " + printer.replace(/\s*\(.*$/, "") : (p.institution ? p.institution.split(",")[0].split(" (")[0] : "Оттиск: цифровой") };
  };
  const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
  const hash = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16); };

  // ---------- model
  async function load() {
    if (D) return D;
    const j = (u, d) => fetch(u).then((r) => (r.ok ? r.json() : d)).catch(() => d);
    const [atlas, thumbs, hist, pairs, ed, cc0, bnp, bsh, reg, plc, spl] = await Promise.all([
      j(E + "data/atlas.json", null), j(E + "data/thumbs.json", {}), j(E + "data/history.json", { cities: [] }),
      j("../poc/compare/pairs/index.json", { places: {}, pairs: [] }), j("editorial.json", {}),
      j("../data/curation/cc0-gallery-20261103.json", { items: [] }), j("../data/curation/benoist-paris-musees-v1.json", { items: [] }), j("benoist-sheets.json", { sheets: [] }), j("benoist-registry.json", { summary: null, works: [] }), j("places.json", { places: [] }), j("sheet-places.json", { sheets: {} }),
    ]);
    // curated records know who made a sheet, who keeps it and on which terms: use them when the url matches
    const known = new Map();
    for (const it of [...(cc0.items || []), ...(bnp.items || [])]) if (it.url) known.set(it.url, it);
    const maker = (m) => String(m || "").replace(/\s*\([^)]*\)\s*$/, "").trim();
    const rightsOf = (it) => (it.license_label || (it.rights === "cc0" ? "CC0" : ""));
    const roles = (it) => (Array.isArray(it.creator_roles) ? it.creator_roles.map((r) => `${r.name} (${r.role})`).join("; ") : "");
    if (!atlas) throw new Error("atlas");
    T = thumbs;
    const histBy = new Map((hist.cities || []).map((h) => [h.city, h]));
    const pairsByCity = new Map();
    for (const id of pairs.pairs || []) {
      const pl = (pairs.places || {})[id]; if (!pl) continue;
      if (!pairsByCity.has(pl.city)) pairsByCity.set(pl.city, []);
      pairsByCity.get(pl.city).push({ id, name: pl.name, mode: pl.mode, image: pl.image, label: (pairs.labels || {})[id] });
    }
    const cities = new Map(), countries = new Map(), plates = new Map();
    for (const c of atlas.cities) {
      const worksByUrl = new Map((c.works || []).map((w) => [w.url, w]));
      const list = [];
      const seenUrl = new Set();
      for (const s of c.sites || []) {
        if (!s.image || seenUrl.has(s.url) || modernPhoto(s.title)) continue; seenUrl.add(s.url);
        const w = worksByUrl.get(s.url) || {};
        list.push({ id: s.wid, city: c.id, kind: "site", title: cap(s.site_ru || cut(clean(s.title), 70)), orig: clean(s.title), image: s.image, url: s.url,
          date: s.date || w.date || (known.get(s.url) || {}).date || "", artist: w.artist || roles(known.get(s.url) || {}) || maker((known.get(s.url) || {}).maker),
          institution: w.institution || (known.get(s.url) || {}).source || holder(s.title, s.url), rights: w.rights_label || rightsOf(known.get(s.url) || {}),
          lat: Number(s.lat), lon: Number(s.lon), qid: s.qid, place: s.site_name || "", conf: s.confidence || "" });
      }
      for (const w of c.works || []) {
        if (!w.image || seenUrl.has(w.url) || modernPhoto(w.title)) continue; seenUrl.add(w.url);
        list.push({ id: "w" + hash(w.url), city: c.id, kind: "work", title: cap(cut(clean(w.title), 70)), orig: clean(w.title), image: w.image, url: w.url,
          date: w.date || (known.get(w.url) || {}).date || "", artist: w.artist || roles(known.get(w.url) || {}) || maker((known.get(w.url) || {}).maker),
          institution: w.institution || (known.get(w.url) || {}).source || holder(w.title, w.url), rights: w.rights_label || rightsOf(known.get(w.url) || {}), lat: NaN, lon: NaN });
      }
      const links = new Map();
      for (const w of c.works || []) {
        if (w.image || !/^https:\/\//.test(w.url || "")) continue;
        const key = w.url + "|" + clean(w.title);
        const e = links.get(key) || { title: cut(clean(w.title), 90), inst: (w.institution || "").split(" (")[0], url: w.url, artist: w.artist || "", n: 0 };
        e.n++; links.set(key, e);
      }
      list.sort((a, b) => (String(a.date || "9999").localeCompare(String(b.date || "9999"))) || a.title.localeCompare(b.title, "ru"));
      list.forEach((p, i) => { p.n = i + 1; p.total = list.length; plates.set(p.id, p); });
      const h = histBy.get(c.name) || null;
      const city = { id: c.id, name: c.name, orig: c.name_orig, country: c.country, area: c.area, lat: c.lat, lon: c.lon, plates: list,
        pairs: pairsByCity.get(c.name) || [], hist: h, kind: c.kind, links: [...links.values()], linkCount: [...links.values()].reduce((n, x) => n + x.n, 0) };
      cities.set(c.id, city);
      if (!countries.has(c.country)) countries.set(c.country, { name: c.country, cities: [] });
      countries.get(c.country).cities.push(city);
    }
    for (const k of countries.values()) {
      k.plates = k.cities.reduce((n, c) => n + c.plates.length, 0);
      k.pairs = k.cities.reduce((n, c) => n + c.pairs.length, 0);
      k.cities = k.cities.filter((c) => c.plates.length || c.pairs.length).sort((a, b) => b.plates.length - a.plates.length || a.name.localeCompare(b.name, "ru"));
    }
    for (const [name, k] of [...countries]) if (!k.plates) countries.delete(name);
    D = { cities, countries, plates, ed, pairs, sheets: (bsh && bsh.sheets) || [], reg, places: (plc && plc.places) || [], sp: (spl && spl.sheets) || {}, total: [...plates.values()].length };
    return D;
  };
  const sortedCountries = () => [...D.countries.values()].sort((a, b) => b.plates - a.plates || a.name.localeCompare(b.name, "ru"));
  const cityLink = (c) => `#/city/${c.id}`;
  const plateLink = (p) => `#/plate/${p.id}`;
  const countryLink = (k) => `#/country/${encodeURIComponent(k.name)}`;

  // matching a plate with a ready "then and now" pair of its city
  const pairFor = (p) => {
    const c = D.cities.get(p.city); if (!c) return null;
    const t = (p.title + " " + p.place).toLowerCase();
    return c.pairs.find((x) => { const n = String(x.name || "").toLowerCase(); return n && (t.includes(n) || n.includes(p.title.toLowerCase())); }) || null;
  };

  // ---------- views
  const crumbs = (items) => {
    $crumbs.innerHTML = items.map((it, i) => (it.href && i < items.length - 1 ? `<a href="${it.href}">${esc(it.t)}</a>` : `<span>${esc(it.t)}</span>`)).join('<span aria-hidden="true">›</span>');
  };
  const setTitle = (t) => { document.title = (t ? t + " · " : "") + "Книга видов · Город на бумаге"; };
  const dock = (next, back) => `<div class="dock">${back ? `<a class="btn ghost" href="${back.href}"><small>Назад</small>${esc(back.t)}</a>` : ""}${next ? `<a class="btn" href="${next.href}"><small>${esc(next.small || "Дальше")}</small>${esc(next.t)} →</a>` : ""}</div>`;

  function viewHome() {
    setTitle(""); crumbs([{ t: "Книга" }]);
    const ed = D.ed || {};
    const ks = sortedCountries();
    const nCities = [...D.cities.values()].filter((c) => c.plates.length).length;
    const featured = (ed.featured || []).map((f) => {
      if (f.pair) { const pl = (D.pairs.places || {})[f.pair]; return pl ? { pair: { id: f.pair, ...pl }, hook: f.hook } : null; }
      const p = D.plates.get(f.plate); return p ? { p, hook: f.hook } : null;
    }).filter(Boolean);
    const seen = seenSet();
    const top = ks.slice(0, 8), rest = ks.slice(8);
    const tocItem = (k) => {
      const read = k.cities.reduce((n, c) => n + c.plates.filter((p) => seen.has(p.id)).length, 0);
      return `<li><a href="${countryLink(k)}"><span class="nm">${esc(k.name)}</span><span class="num">${plural(k.cities.length, "город", "города", "городов")} · ${plural(k.plates, "вид", "вида", "видов")}${k.pairs ? " · " + plural(k.pairs, "сравнение", "сравнения", "сравнений") : ""}</span>
        <span class="sub">${esc(k.cities.slice(0, 4).map((c) => c.name).join(", "))}${k.cities.length > 4 ? " и другие" : ""}</span>${read ? `<span class="bar" aria-label="Просмотрено ${read} из ${k.plates}"><i style="width:${Math.round(100 * read / k.plates)}%"></i></span>` : ""}</a></li>`;
    };
    $app.innerHTML = `<div class="page-enter">
      <section class="cover">
        <p class="eyebrow">Книга видов · цифровое издание</p>
        <h1>${esc(ed.title || "Города на бумаге")}</h1>
        <p class="lede">${esc(ed.subtitle || "Старые литографии и гравюры городов. У каждого листа есть место на карте, а у некоторых и фотография сегодня.")}</p>
        <div class="stats"><span><b>${ks.length}</b>${plural(ks.length, "страна", "страны", "стран").replace(/^\d+ /, "")}</span><span><b>${nCities}</b>${plural(nCities, "город", "города", "городов").replace(/^\d+ /, "")}</span><span><b>${D.total}</b>${plural(D.total, "лист", "листа", "листов").replace(/^\d+ /, "")}</span></div>
        <div class="btn-row"><a class="btn" href="#main">Начать с главных видов ↓</a><a class="btn ghost" href="#toc">Оглавление</a></div>
      </section>
      <section class="preface" aria-label="Предисловие">
        <p class="eyebrow">Предисловие</p>
        ${(ed.preface || ["Когда-то путеводитель вёл читателя за руку: сначала главное, потом город за городом. Мы собрали книгу так же.", "Листайте: у каждого листа сказано, кто его нарисовал и где хранится оригинал. Там, где нашли фото того же места, можно сравнить «тогда» и «сейчас»."]).map((t) => `<p>${esc(t)}</p>`).join("")}
        <ul class="howto"><li>Сначала главные виды, потом оглавление по странам.</li><li>В главе города видно, сколько в нём листов и сравнений.</li><li>Внизу экрана всегда кнопка «Дальше».</li></ul>
      </section>
      ${featured.length ? `<h2 id="main">Главные виды</h2><div class="strip" role="list">${featured.map(({ p, hook, pair }) => pair
        ? `<a class="feat pairc" role="listitem" href="../poc/compare/?journey=1#${esc(pair.id)}"><img src="../poc/compare/pairs/${esc(pair.image)}" alt="" loading="lazy"><span class="cap"><span class="where">${esc(pair.city)} · тогда и сейчас</span><b>${esc(pair.name)}</b><span class="hook">${esc(hook || "")}</span></span></a>`
        : `<a class="feat" role="listitem" href="${plateLink(p)}">${img(p.image, p.title, "", 600)}<span class="cap"><span class="where">${esc(D.cities.get(p.city).name)}${p.date ? " · " + esc(p.date) : ""}</span><b>${esc(p.title)}</b><span class="hook">${esc(hook || "")}</span></span></a>`).join("")}</div>` : '<span id="main"></span>'}
      <a class="theme" href="#/exhibitions"><span class="lt-small">Залы</span><b>Выставки</b><span>Рим, Венеция, исчезнувший Париж: сорок с лишним работ Пиранези, Каналетто, Мерьона и других, все открыты музеями.</span></a>
      <a class="theme" href="#/albums"><span class="lt-small">Книги целиком</span><b>Исторические альбомы</b><span>«Paris dans sa splendeur» (1861): 71 планша в порядке издания, с обложкой и ссылкой на страницу библиотеки.</span></a>
      <a class="theme" href="#/benoist"><span class="lt-small">Тема издания</span><b>Листы Бенуа</b><span>Как читать подпись литографии, где есть листы Филиппа и Феликса Бенуа и как сравнить их с фото сегодня.</span></a>
      <a class="theme" href="#/catalog"><span class="lt-small">Реестр</span><b>Собрание</b><span>Все найденные листы Бенуа по авторам, сериям, странам и городам: сколько найдено, сколько проверено и сколько можно показать.</span></a>
      <a class="theme" href="#/timeline"><span class="lt-small">По годам</span><b>Хронология</b><span>Листы от 1790-х до 1880-х: двигайте ползунки и смотрите, что печатали в каждое десятилетие.</span></a>
      <a class="theme" href="#/places"><span class="lt-small">Истории</span><b>Истории мест</b><span>Нотр-Дам, Сент-Шапель, колоннада Лувра, Пале-Рояль и утраченный дворец Тюильри: факты с датами и ссылками на источники.</span></a>
      <h2 id="toc">Оглавление</h2>
      <ol class="toc">${top.map(tocItem).join("")}</ol>
      ${rest.length ? `<details class="more-toc"><summary class="btn ghost wide">Ещё ${plural(rest.length, "страна", "страны", "стран")}</summary><ol class="toc">${rest.map(tocItem).join("")}</ol></details>` : ""}
    </div>`;
  }

  function viewCountry(name) {
    const k = D.countries.get(name); if (!k) return notFound();
    setTitle(k.name); crumbs([{ t: "Книга", href: "#/" }, { t: k.name }]);
    const idx = sortedCountries().findIndex((x) => x.name === k.name), nextK = sortedCountries()[idx + 1];
    $app.innerHTML = `<div class="page-enter"><section class="chead"><p class="eyebrow">Страна</p><h1>${esc(k.name)}</h1>
      <div class="counts"><span>${plural(k.cities.length, "город", "города", "городов")}</span><span>${plural(k.plates, "вид", "вида", "видов")}</span>${k.pairs ? `<span>${plural(k.pairs, "сравнение", "сравнения", "сравнений")}</span>` : ""}</div></section>
      <div class="cards">${k.cities.map((c) => { const p = c.plates[0]; return `<a class="card" href="${cityLink(c)}">${p ? img(p.image, "", "", 300) : '<span class="ph"></span>'}<span class="body"><b>${esc(c.name)}</b><span class="meta">${plural(c.plates.length, "вид", "вида", "видов")}${c.pairs.length ? " · " + plural(c.pairs.length, "сравнение", "сравнения", "сравнений") : ""}</span><span class="tag">${esc(c.hist ? c.hist.tagline : ((D.ed.cityHooks || {})[c.id] || ""))}</span></span></a>`; }).join("")}</div>
      ${dock(nextK ? { href: countryLink(nextK), t: nextK.name, small: "Следующая страна" } : null, { href: "#/", t: "Оглавление" })}</div>`;
  }

  function viewCity(id) {
    const c = D.cities.get(id); if (!c) return notFound();
    const countryObj = D.countries.get(c.country) || null;
    setTitle(c.name); crumbs(countryObj ? [{ t: "Книга", href: "#/" }, { t: c.country, href: countryLink({ name: c.country }) }, { t: c.name }] : [{ t: "Книга", href: "#/" }, { t: c.name }]);
    const seen = seenSet(); const read = c.plates.filter((p) => seen.has(p.id)).length;
    const h = c.hist;
    const starIds = (D.ed.cityStars || {})[c.id];
    const stars = (starIds ? starIds.map((x) => D.plates.get(x)).filter(Boolean)
      : c.plates.filter((p) => p.kind === "site").sort((a, b) => (b.conf === "high") - (a.conf === "high") || (pairFor(b) ? 1 : 0) - (pairFor(a) ? 1 : 0)).slice(0, 5));
    const siblings = countryObj ? countryObj.cities : [], i = siblings.findIndex((x) => x.id === c.id), nextC = siblings[i + 1];
    const first = c.plates.find((p) => !seen.has(p.id)) || c.plates[0];
    const chap = (D.ed.chapters || {})[c.id] || null;
    const qa = (q, a) => `<p class="q">${esc(q)}</p><details class="ans"><summary>Показать ответ</summary><p>${esc(a)}</p></details>`;
    const view = (v) => {
      const pl = v.plate ? D.plates.get(v.plate) : null, pr = v.pair ? (D.pairs.places || {})[v.pair] : null;
      const href = v.href || (pr ? `../poc/compare/?journey=1#${v.pair}` : pl ? plateLink(pl) : "#/");
      const im = v.image ? `<img src="${esc(v.image)}" alt="" loading="lazy">` : pr ? `<img src="../poc/compare/pairs/${esc(pr.image)}" alt="" loading="lazy">` : pl ? img(pl.image, v.title, "", 700) : "";
      return `<article class="view"><a class="vimg" href="${href}">${im}</a><div class="vbody"><h3>${esc(v.title)}</h3><p class="small">${esc(v.who || "")}</p>${qa(v.q, v.a)}<a class="btn ghost" href="${href}">${pr || v.href ? "Сравнить с фото →" : "Открыть лист →"}</a></div></article>`;
    };
    const chapterHtml = chap ? `<p class="lede">${esc(chap.lede)}</p><h2>Три главных вида</h2><div class="views">${chap.views.map(view).join("")}</div>` : "";
    const chapterTail = chap ? `${chap.extra ? chap.extra.map((x) => `<div class="fact"><b>${esc(x.t)}</b>${qa(x.q, x.a)}</div>`).join("") : ""}
      <h2>Что изменилось</h2><ol class="tl">${chap.timeline.map(([y, t]) => `<li><b>${esc(y)}</b><span>${esc(t)}</span></li>`).join("")}</ol>
      <h2>Старые путеводители</h2><ul class="bl">${chap.books.map(([t, d]) => `<li><b>${esc(t)}</b><span>${esc(d)}</span></li>`).join("")}</ul>
      <div class="fact"><b>Знаете ли вы</b>${esc(chap.fact)}</div>
      <p class="outro">${esc(chap.outro)}</p>` : "";
    const archive = c.linkCount ? `<details class="archive"><summary class="btn ghost wide">Ещё ${plural(c.linkCount, "лист", "листа", "листов")} у хранителей (откроются на их сайтах)</summary><ul>${c.links.map((l) => `<li><a href="${esc(safe(l.url))}" target="_blank" rel="noopener noreferrer">${esc(l.title)}${l.n > 1 ? " ×" + l.n : ""}</a><span class="small"> ${esc(l.inst)}</span></li>`).join("")}</ul><p class="small">Здесь показаны только листы, которые можно открыть свободно. Остальные защищены правом или хранятся на сайтах архивов.</p></details>` : "";
    let shown = 12;
    const grid = () => c.plates.slice(0, shown).map((p) => `<a class="pl${seen.has(p.id) ? " seen" : ""}" href="${plateLink(p)}">${pairFor(p) ? '<span class="pair">СРАВНИТЬ</span>' : ""}${img(p.image, p.title, "", 400)}<span class="t">${esc(p.title)}<span class="d">${esc(p.date || "дата у хранителя")}</span></span></a>`).join("");
    $app.innerHTML = `<div class="page-enter"><section class="chead"><p class="eyebrow">${esc(c.country)}${c.area ? " · " + esc(c.area) : ""}</p><h1>${esc(c.name)}</h1>
      ${h ? `<p class="lede">${esc(h.tagline)}</p>` : ""}
      <div class="counts"><span>${plural(c.plates.length, "лист здесь", "листа здесь", "листов здесь")}</span>${c.linkCount ? `<span>${plural(c.linkCount, "лист", "листа", "листов")} у хранителей</span>` : ""}${c.pairs.length ? `<span>${plural(c.pairs.length, "сравнение", "сравнения", "сравнений")}</span>` : ""}${c.plates.length ? `<span>просмотрено ${read} из ${c.plates.length}</span>` : ""}</div></section>
      ${chapterHtml}
      ${!chap && stars.length ? `<h2>Главные виды города</h2><div class="strip" role="list">${stars.map((p) => `<a class="feat" role="listitem" href="${plateLink(p)}">${img(p.image, p.title, "", 600)}<span class="cap"><span class="where">${esc(p.date || c.name)}</span><b>${esc(p.title)}</b></span></a>`).join("")}</div>` : ""}
      ${h ? `<div class="intro"><p>${esc(h.intro.split(/(?<=[.!?])\s/).slice(0, 2).join(" "))}</p>
        <details class="story"><summary class="btn ghost wide">Читать историю города</summary><p>${esc(h.intro)}</p>${(h.chapters || []).map((ch) => `<h3>${esc(ch.title)}</h3><p>${esc(ch.text)}</p>`).join("")}</details>
        ${h.did_you_know && h.did_you_know[0] ? `<div class="fact"><b>Знаете ли вы</b>${esc(typeof h.did_you_know[0] === "string" ? h.did_you_know[0] : (h.did_you_know[0].text || ""))}</div>` : ""}</div>` : ""}
      ${c.pairs.length ? `<h2>Сравнить с фото сегодня</h2><div class="cards">${c.pairs.map((x) => `<a class="card" href="../poc/compare/?journey=1#${esc(x.id)}"><img src="../poc/compare/pairs/${esc(x.image)}" alt="" loading="lazy"><span class="body"><b>${esc(x.name)}</b><span class="meta">Тогда и сейчас</span><span class="tag">${esc(x.mode || "")}</span></span></a>`).join("")}</div>` : ""}
      ${c.plates.length ? `<h2>Листы города</h2><div class="plates" id="grid">${grid()}</div><div class="btn-row"><button type="button" class="btn ghost wide" id="moreBtn" ${c.plates.length <= shown ? "hidden" : ""}>Показать ещё ${Math.min(12, c.plates.length - shown)}</button></div>` : `<div class="nolook"><b>Открытых листов для показа в книге пока нет.</b> ${c.linkCount ? "Ниже собраны ссылки на оригиналы у хранителей." : "Мы собираем проверенные листы для этого города."}</div>`}
      ${c.plates.some((p) => Number.isFinite(p.lat)) ? `<h2>Где это в городе</h2><div class="lmap" id="lmap" role="region" aria-label="Карта: места листов"></div><p class="small">Нажмите метку, чтобы открыть лист.</p>` : ""}
      ${archive}
      ${chapterTail}
      ${dock(chap && chap.next && !first ? null : first ? { href: plateLink(first), t: first.title, small: read ? "Продолжить" : "Начать с первого листа" } : nextC ? { href: cityLink(nextC), t: nextC.name, small: "Следующий город" } : null, countryObj ? { href: countryLink({ name: c.country }), t: c.country } : { href: "#/", t: "Оглавление" })}</div>`;
    const more = document.getElementById("moreBtn");
    if (more) more.onclick = () => { shown += 12; document.getElementById("grid").innerHTML = grid(); more.textContent = `Показать ещё ${Math.min(12, c.plates.length - shown)}`; more.hidden = shown >= c.plates.length; };
    mountMap("lmap", c.plates.filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon)), null);
  }

  function viewPlate(id) {
    const p = D.plates.get(id); if (!p) return notFound();
    const c = D.cities.get(p.city); markSeen(p.id);
    setTitle(p.title); crumbs([{ t: "Книга", href: "#/" }, { t: c.country, href: countryLink({ name: c.country }) }, { t: c.name, href: cityLink(c) }, { t: "Лист " + p.n }]);
    const prev = c.plates[p.n - 2], next = c.plates[p.n];
    const pair = pairFor(p);
    const hasGeo = Number.isFinite(p.lat) && Number.isFinite(p.lon);
    const ed = (D.ed.plateNotes || {})[p.id];
    const plateEntry = { place: hasGeo ? { name: p.title, city: c.name, lat: p.lat, lon: p.lon, approximate: true, href: `${E}#/city/${c.id}` } : null,
      pairs: pair ? [{ id: pair.id, status_ru: "Сравнение из музея: рисунок и фото одного места", photo: null }] : [] };
    $app.innerHTML = `<article class="plate page-enter"><p class="eyebrow">${esc(c.name)} · лист ${p.n} из ${p.total}</p>
      <figure class="lt-sheet"><div class="lt-print">${img(p.image, p.title, "", 960)}</div>
        <div class="lt-imprint"><span class="l">${esc(imprint(p).left)}</span><span class="c">№ ${p.n}</span><span class="r">${esc(imprint(p).right)}</span></div>
        <figcaption class="lt-caption">${esc(p.title)}${p.orig && p.orig !== p.title ? `<small>${esc(p.orig)}</small>` : ""}</figcaption></figure>
      <div class="lt-divider" aria-hidden="true"></div>
      <h1 class="sr-title">${esc(p.title)}</h1>
      ${ed ? `<p class="lede">${esc(ed)}</p>` : ""}
      <ul class="facts">
        <li><b>Автор</b><span>${esc(p.artist || "указан в записи хранителя")}</span></li>
        <li><b>Дата</b><span>${esc(p.date || "указана в записи хранителя")}</span></li>
        <li><b>Хранится</b><span>${esc(p.institution || "Викисклад (собрание указано на странице файла)")}</span></li>
        <li><b>Права</b><span>${esc(p.rights || "условия указаны на странице источника")}</span></li>
      </ul>
      ${compareSection(plateEntry)}
      ${placeSection(plateEntry)}
      <div class="btn-row"><a class="btn ghost" href="${esc(safe(p.url))}" target="_blank" rel="noopener noreferrer">Оригинал у хранителя ↗︎</a></div>
      ${dock(next ? { href: plateLink(next), t: next.title, small: `Лист ${next.n} из ${p.total}` } : { href: cityLink(c), t: "К главе города", small: "Это последний лист" }, prev ? { href: plateLink(prev), t: "Назад" } : { href: cityLink(c), t: c.name })}</article>`;
    mountPlace(plateEntry); wireAngles(plateEntry);
    const pr = $app.querySelector(".plate .lt-print"), pim = pr && pr.querySelector("img");
    if (pim) {
      const ctl = document.createElement("div"); ctl.className = "lt-tool zoomctl";
      ctl.innerHTML = `<label for="pzr"><span class="lt-legend">Увеличение</span> <b id="pzv">100%</b></label><input id="pzr" type="range" min="100" max="300" step="10" value="100">`;
      pr.closest("figure").after(ctl);
      const zr = ctl.querySelector("input");
      zr.addEventListener("input", () => { pr.classList.add("zoomable"); pim.style.width = zr.value + "%"; pim.style.maxWidth = "none"; document.getElementById("pzv").textContent = zr.value + "%"; });
    }
    // swipe left/right turns the page (not while dragging the map)
    const art = $app.querySelector(".plate"); let sx = null, sy = 0;
    art.addEventListener("touchstart", (e) => { sx = e.target.closest(".lmap") ? null : e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
    art.addEventListener("touchend", (e) => {
      if (sx === null) return;
      const dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy; sx = null;
      if (Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 1.8) { const to = dx < 0 ? next : prev; if (to) location.hash = plateLink(to); }
    }, { passive: true });
  }

  const BENOIST = /Benoist|Бенуа/i;
  const SIGN = [
    { id: "city", x: 49, y: 12, t: "«Paris»", d: "Город. Так подписан лист: это вид Парижа." },
    { id: "draw", x: 14, y: 86, t: "«Ph. Benoist»", d: "Автор рисунка. В записи Библиотеки Конгресса: «Ph. Benoist del.». Слово del. сокращение от латинского delineavit, «нарисовал». Кто переносил рисунок на камень, на этом листе не сказано." },
    { id: "num", x: 46, y: 84, t: "«8»", d: "Номер листа в серии видов. По номеру можно найти соседние листы и понять, из какого набора этот вид." },
    { id: "print", x: 85, y: 86, t: "«Imp. Lemercier, Paris»", d: "Печатня. Imp. значит imprimerie, «типография». Так подписана печатня, где сделан этот оттиск с литографского камня." },
    { id: "title", x: 66, y: 93, t: "«LA MADELEINE.»", d: "Название по-французски: церковь Мадлен в Париже." },
  ];
  function viewBenoist() {
    setTitle("Листы Бенуа"); crumbs([{ t: "Книга", href: "#/" }, { t: "Листы Бенуа" }]);
    const cities = [...D.cities.values()].map((c) => ({ c, n: c.plates.filter((p) => BENOIST.test(p.artist)).length + c.links.filter((l) => BENOIST.test(l.artist)).reduce((n, l) => n + l.n, 0) })).filter((x) => x.n).sort((a, b) => b.n - a.n);
    const open = [...D.plates.values()].filter((p) => BENOIST.test(p.artist)).slice(0, 8);
    const pairs = ["madeleine-benoist-carnavalet", "madeleine-ph-benoist", "palais-royal-ph-benoist", "naples-san-francesco-di-paola"].map((id) => ({ id, pl: (D.pairs.places || {})[id], label: (D.pairs.labels || {})[id] })).filter((x) => x.label);
    $app.innerHTML = `<div class="page-enter">
      <section class="chead"><p class="eyebrow">Тема издания</p><h1>Листы Бенуа</h1><p class="lede">В музейных записях два мастера с этой фамилией: Филипп и Феликс Бенуа. Они рисовали города для печатных альбомов. Родство между ними по доступным источникам не установлено.</p></section>
      <h2>Как читать подпись литографии</h2>
      <p class="small">Нажмите на цифру, чтобы прочитать, что написано на листе.</p>
      <figure class="lt-sheet sign" id="sign"><div class="lt-print"><img src="../assets/web/eras-img-paris-madeleine-1845-60-benoist-lemercier-loc-pga-14315-720.jpg" alt="Литография «Мадлен», Ph. Benoist, печатня Lemercier, Париж" width="720" height="527">
        ${SIGN.map((h, i) => `<button type="button" class="hot" data-i="${i}" style="left:${h.x}%;top:${h.y}%" aria-label="${esc(h.t)}">${i + 1}</button>`).join("")}</div>
        <figcaption class="lt-caption">Мадлен<small>Библиотека Конгресса США, LC-DIG-pga-14315 · ограничений на публикацию не известно</small></figcaption></figure>
      <div class="lt-tool" role="status" aria-live="polite" id="signNote"><span class="lt-legend">Надпись ${1}</span><p><b>${esc(SIGN[0].t)}</b>. ${esc(SIGN[0].d)}</p></div>
      <div class="lt-divider" aria-hidden="true"></div>
      <h2>Где есть листы Бенуа</h2>
      <ol class="toc">${cities.slice(0, 12).map(({ c, n }) => `<li><a href="${cityLink(c)}"><span class="nm">${esc(c.name)}</span><span class="num">${plural(n, "лист", "листа", "листов")}</span><span class="sub">${esc(c.country)}</span></a></li>`).join("")}</ol>
      ${pairs.length ? `<h2>Сравнить Бенуа с фото</h2><div class="cards">${pairs.map((x) => `<a class="card" href="../poc/compare/?journey=1#${esc(x.id)}">${x.pl ? `<img src="../poc/compare/pairs/${esc(x.pl.image)}" alt="" loading="lazy">` : '<span class="ph"></span>'}<span class="body"><b>${esc(x.label)}</b><span class="meta">Тогда и сейчас</span></span></a>`).join("")}</div>` : ""}
      ${open.length ? `<h2>Листы, которые можно открыть здесь</h2><div class="plates">${open.map((p) => `<a class="pl" href="${plateLink(p)}">${img(p.image, p.title, "", 400)}<span class="t">${esc(p.title)}<span class="d">${esc(D.cities.get(p.city).name)}</span></span></a>`).join("")}</div>` : ""}
      ${D.sheets.length ? `<div class="lt-divider" aria-hidden="true"></div><h2>Листы из открытых музеев</h2>
        <p class="small">${plural(D.sheets.length, "лист", "листа", "листов")} с открытой лицензией на файл: Paris Musées (CC0) и Rijksmuseum (Public Domain Mark). Участников и роли мы пишем так, как их называет музей, без своих догадок. <a href="#/catalog">Весь реестр найденных листов →</a></p>
        <div class="bsheets" id="bsheets">${D.sheets.map((s, n) => `<figure class="lt-sheet bsheet"${n >= 24 ? " hidden" : ""}><a class="lt-print zoomlink" href="#/sheet/${esc(s.id)}" aria-label="Открыть лист крупно: ${esc(s.title)}"><img src="${esc(s.image)}" alt="${esc(s.title)}" loading="lazy" width="900"></a>
          <figcaption class="lt-caption">${esc(s.title.split(" / ")[0])}<small>${s.creators && s.creators.length ? s.creators.map((c) => esc(c.role_ru) + ": " + esc(c.name)).join(" · ") : "По записи музея: " + s.participants.map(esc).join(" · ") + " (роли в записи не указаны)"}</small></figcaption>
          <p class="bs-meta">${esc(s.holder)} · ${esc(s.accession)} · <a href="${esc(safe(s.rights_url))}" target="_blank" rel="noopener">${esc(s.rights)}</a> · <a href="${esc(safe(s.record_url))}" target="_blank" rel="noopener">карточка музея</a>${s.extra_impressions ? " · в музее есть ещё " + plural(s.extra_impressions, "экземпляр", "экземпляра", "экземпляров") + " этого листа" : ""}</p></figure>`).join("")}</div>${D.sheets.length > 24 ? `<p class="btn-row"><button type="button" class="btn ghost" id="bsMore">Показать ещё листы</button></p>` : ""}` : ""}
      ${dock({ href: cityLink(D.cities.get("paris")), t: "Париж с Бенуа", small: "Дальше" }, { href: "#/", t: "Оглавление" })}</div>`;
    const bm = document.getElementById("bsMore");
    if (bm) bm.addEventListener("click", () => {
      const hid = [...document.querySelectorAll("#bsheets .bsheet[hidden]")];
      hid.slice(0, 24).forEach((f) => f.removeAttribute("hidden"));
      if (hid.length <= 24) bm.parentElement.remove();
    });
    const note = document.getElementById("signNote");
    document.querySelectorAll("#sign .hot").forEach((b) => b.addEventListener("click", () => {
      const h = SIGN[Number(b.dataset.i)];
      document.querySelectorAll("#sign .hot").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      note.innerHTML = `<span class="lt-legend">Надпись ${Number(b.dataset.i) + 1}</span><p><b>${esc(h.t)}</b>. ${esc(h.d)}</p>`;
    }));
  }


  // ---------- one sheet, large, with a zoom slider and neighbours
  const ARTIST = { "philippe-benoist": "Филипп Бенуа", "felix-benoist": "Феликс Бенуа", "uncertain-benoist": "Бенуа, имя не уточнено", other: "Другие авторы" };
  // display-only looks for a sheet (edge kernel adapted from the Gemini "computer-vision" portable package, v10)
  function sobelEdges(src) {
    const { width: w, height: h, data } = src, g = new Float32Array(w * h), out = new Uint8ClampedArray(data.length).fill(255);
    for (let p = 0; p < w * h; p++) { const i = p * 4; g[p] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]; }
    for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
      const p = y * w + x;
      const gx = -g[p - w - 1] + g[p - w + 1] - 2 * g[p - 1] + 2 * g[p + 1] - g[p + w - 1] + g[p + w + 1];
      const gy = -g[p - w - 1] - 2 * g[p - w] - g[p - w + 1] + g[p + w - 1] + 2 * g[p + w] + g[p + w + 1];
      const v = Math.max(0, Math.min(255, Math.round(255 - Math.hypot(gx, gy) * 1.2))), i = p * 4;
      out[i] = out[i + 1] = out[i + 2] = v;
    }
    return new ImageData(out, w, h);
  }
  function wireLens(im) {
    const btns = document.querySelectorAll(".lensbtn"); if (!btns.length) return;
    let cv = null;
    const press = (k) => btns.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lens === k)));
    const set = (k) => {
      press(k);
      im.style.filter = k === "contrast" ? "contrast(1.4)" : k === "shadow" ? "brightness(1.18) contrast(1.08)" : "";
      if (cv) { cv.remove(); cv = null; }
      im.style.display = "";
      if (k !== "edges") return;
      const draw = () => {
        try {
          const c = document.createElement("canvas"), w = im.naturalWidth, h = im.naturalHeight; c.width = w; c.height = h;
          const x = c.getContext("2d"); x.drawImage(im, 0, 0); x.putImageData(sobelEdges(x.getImageData(0, 0, w, h)), 0, 0);
          c.style.cssText = "display:block;max-width:none;height:auto;width:" + (im.style.width || "100%"); c.setAttribute("role", "img"); c.setAttribute("aria-label", "Контуры листа, показ на экране");
          cv = c; im.style.display = "none"; im.parentNode.append(c);
        } catch (e) { press("orig"); }
      };
      im.complete && im.naturalWidth ? draw() : im.addEventListener("load", draw, { once: true });
    };
    btns.forEach((b) => b.addEventListener("click", () => set(b.dataset.lens)));
    document.getElementById("zoomrange").addEventListener("input", () => { if (cv) cv.style.width = im.style.width; });
  }
  // outside <-> inside of one building, only from sheets the book really has (no interior is ever borrowed from another hall)
  const isInterior = (x) => /int[eé]rieur|interior|innen|binnen|galerie d/i.test(x.title);
  function insideOutside(sh) {
    const pid = ((D.sp[sh.id] || {}).place || {}).id; if (!pid) return "";
    const kin = D.sheets.filter((x) => x.id !== sh.id && ((D.sp[x.id] || {}).place || {}).id === pid && isInterior(x) !== isInterior(sh)).slice(0, 4);
    if (!kin.length) return "";
    const inside = isInterior(sh);
    return `<h2>${inside ? "Снаружи того же здания" : "Войти внутрь"}</h2><p class="small">${inside ? "Этот лист показывает внутреннее помещение. Фасад и город вокруг — на листах ниже." : "Для этого здания в книге есть лист с интерьером. Современный снимок помещения показан только там, где он действительно из этого зала."}</p>
      <div class="plates">${kin.map((x) => `<a class="pl" href="#/sheet/${esc(x.id)}"><img src="${esc(x.image)}" alt="" loading="lazy" width="400"><span class="t">${esc(cut(x.title.split(" / ")[0], 40))}</span><span class="s">${esc(x.holder)}</span></a>`).join("")}</div>`;
  }
  const placeForSheet = (sh) => D.places.find((x) => (x.related_sheet_ids || []).includes(sh.id)) || null;
  function viewSheet(id) {
    const i = D.sheets.findIndex((x) => x.id === id), sh = D.sheets[i];
    if (!sh) return notFound();
    const prev = D.sheets[i - 1], next = D.sheets[i + 1];
    const title = sh.title.split(" / ")[0];
    const pl = placeForSheet(sh);
    setTitle(title); crumbs([{ t: "Книга", href: "#/" }, { t: "Листы Бенуа", href: "#/benoist" }, { t: cut(title, 28) }]);
    const who = sh.creators && sh.creators.length ? sh.creators.map((c) => `<li><b>${esc(c.role_ru)}</b> ${esc(c.name)}</li>`).join("")
      : (sh.participants || []).map((n) => `<li>${esc(n)}</li>`).join("") + `<li class="small">Роли в записи музея не указаны.</li>`;
    const more = (sh.impressions || []).map((m) => `<a href="${esc(safe(m.record_url))}" target="_blank" rel="noopener">${esc(m.accession)}</a>`).join(", ");
    $app.innerHTML = `<div class="page-enter plate">
      <section class="chead"><p class="eyebrow">Лист ${i + 1} из ${D.sheets.length} · ${esc(sh.holder)}</p><h1>${esc(title)}</h1></section>
      <figure class="lt-sheet"><div class="zoomwrap" id="zoomwrap" tabindex="0" aria-label="Лист крупно. Прокручивайте, чтобы рассмотреть детали"><img id="zoomimg" src="${esc(sh.image)}" alt="${esc(sh.title)}" width="1280"></div>
        <div class="lt-tool zoomctl"><label for="zoomrange"><span class="lt-legend">Увеличение</span> <b id="zoomval">100%</b></label><input id="zoomrange" type="range" min="100" max="300" step="10" value="100"></div>
        ${deepControls}
        <details class="lt-tool lens"><summary>Рассмотреть иначе: контраст, тени, контур</summary><div class="lensrow" role="group" aria-label="Как рассмотреть лист">${[["orig", "Оригинал"], ["contrast", "Контраст"], ["shadow", "Тени"], ["edges", "Контур"]].map(([k, t]) => `<button type="button" class="btn ghost lensbtn" data-lens="${k}" aria-pressed="${k === "orig"}">${t}</button>`).join("")}</div><p class="small">Только показ на экране: файл не меняется. Это не научный снимок и не «реставрация».</p></details>
        <figcaption class="lt-imprint"><span class="l">${esc(sh.holder)}</span><span class="c">${esc(sh.rights)}</span><span class="r">${esc(sh.accession)}</span></figcaption></figure>
      <h2>Кто сделал лист</h2><ul class="facts-list">${who}</ul>
      <h2>Что известно</h2><dl class="facts"><dt>Техника</dt><dd>${esc(sh.technique || "в записи не указана")}</dd><dt>Права</dt><dd><a href="${esc(safe(sh.rights_url))}" target="_blank" rel="noopener">${esc(sh.rights)}</a></dd>
        <dt>Оригинал</dt><dd><a href="${esc(safe(sh.record_url))}" target="_blank" rel="noopener">карточка в собрании ↗</a></dd>${more ? `<dt>Другие экземпляры</dt><dd>${more}</dd>` : ""}</dl>
      ${insideOutside(sh)}
      ${pl ? `<h2>История места</h2><p><a class="btn ghost" href="#/place/${esc(pl.id)}">${esc(pl.name_ru)}: что стояло, что изменилось →</a></p>` : ""}
      ${placeSection(D.sp[sh.id])}
      ${compareSection(D.sp[sh.id])}
      ${dock(next ? { href: "#/sheet/" + next.id, t: cut(next.title.split(" / ")[0], 26), small: "Следующий лист" } : { href: "#/benoist", t: "Все листы Бенуа" }, prev ? { href: "#/sheet/" + prev.id, t: cut(prev.title.split(" / ")[0], 22) } : { href: "#/benoist", t: "Листы Бенуа" })}</div>`;
    const range = document.getElementById("zoomrange"), im = document.getElementById("zoomimg"), val = document.getElementById("zoomval");
    range.addEventListener("input", () => { im.style.width = range.value + "%"; val.textContent = range.value + "%"; });
    wireLens(im); wireDeepZoom(sh.image, sh.title);
    mountPlace(D.sp[sh.id]); wireAngles(D.sp[sh.id]);
  }

  const workRow = (w, byImg) => { const sh = w.image && byImg.get(w.image);
      return `<li class="cw">${sh ? `<a class="th" href="#/sheet/${esc(sh.id)}"><img src="${esc(sh.image)}" alt="" loading="lazy" width="96"></a>` : `<span class="th none" aria-hidden="true">нет файла</span>`}
        <div><b><a class="wtitle" href="${sh ? "#/sheet/" + esc(sh.id) : "#/work/" + esc(w.id)}">${esc(cut(String(w.title || "Без названия").split(" / ")[0], 70))}</a></b>
        <span class="sub">${[ARTIST[w.artist], w.series, w.city, w.date].filter(Boolean).map(esc).join(" · ")}</span>
        <span class="sub">${w.impressions > 1 ? plural(w.impressions, "экземпляр", "экземпляра", "экземпляров") + " · " : ""}${w.open_file ? "изображение открыто" : "только ссылка на хранителя"}${sh ? ` · <a href="#/sheet/${esc(sh.id)}">лист в книге</a>` : ""}${(w.links || [])[0] ? ` · <a class="ext" href="${esc(safe(w.links[0].u))}" target="_blank" rel="noopener">${esc(w.links[0].i || "в собрании")} ↗</a>` : ""}</span></div></li>`; };

  // ---------- the collection register: author -> series -> country -> city -> work, with honest counters
  const catState = { artist: "", series: "", country: "", city: "", take: 40 };
  function viewCatalog(artist) {
    setTitle("Собрание"); crumbs([{ t: "Книга", href: "#/" }, { t: "Собрание" }]);
    const R = D.reg || { works: [], summary: null }, sum = R.summary;
    if (!sum) return notFound();
    const byImg = new Map(D.sheets.map((x) => [x.image, x]));
    const artists = Object.entries(sum.by_artist).sort((a, b) => b[1] - a[1]);
    const cur = artist && sum.by_artist[artist] ? artist : "";
    if (catState.artist !== cur) { catState.artist = cur; catState.take = 40; }
    const pool = R.works.filter((w) => !cur || w.artist === cur);
    const uniq = (k) => [...new Set(pool.map((w) => w[k]).filter(Boolean))].sort((a, b) => a.localeCompare(b, "ru"));
    const facets = { series: uniq("series"), country: uniq("country"), city: uniq("city") };
    for (const k of ["series", "country", "city"]) if (catState[k] && !facets[k].includes(catState[k])) catState[k] = "";
    const hasFilter = Boolean(catState.series || catState.country || catState.city);
    const list = pool.filter((w) => (!catState.series || w.series === catState.series) && (!catState.country || w.country === catState.country) && (!catState.city || w.city === catState.city));
    const chips = (k, vals, label) => vals.length ? `<div class="chips" role="group" aria-label="${label}"><button type="button" data-k="${k}" data-v="" aria-pressed="${!catState[k]}">Все</button>${vals.map((v) => `<button type="button" data-k="${k}" data-v="${esc(v)}" aria-pressed="${catState[k] === v}">${esc(cut(v, 28))}</button>`).join("")}</div>` : "";
    const row = (w) => workRow(w, byImg);
    $app.innerHTML = `<div class="page-enter">
      <section class="chead"><p class="eyebrow">Реестр произведений</p><h1>Собрание</h1>
        <p class="lede">Сколько листов найдено и сколько из них можно показать. Записи без права показа остаются ссылками на хранителя: мы не копируем то, что копировать нельзя.</p></section>
      <dl class="stats"><div><dt>Записей найдено</dt><dd>${sum.discovered_records}</dd></div><div><dt>Разных листов, оценка</dt><dd>${sum.unique_works}</dd></div><div><dt>Записи прочитаны</dt><dd>${sum.reviewed}</dd></div><div><dt>Открытые файлы</dt><dd>${sum.open_file}</dd></div><div><dt>Листов в книге</dt><dd>${D.sheets.length}</dd></div></dl>
      <p class="small">«Разных листов»: записи об одном листе в разных каталогах склеены, когда совпадение надёжно (склеено ${sum.merged_by_high_groups || 0}). Ещё ${sum.possible_merges_medium || 0} пар куратору предстоит проверить глазами; без склейки было бы ${sum.unique_works_strict || sum.unique_works}.</p>
      <div class="chips" role="group" aria-label="Автор"><a class="chip" href="#/catalog"${!cur ? ' aria-current="page"' : ""}>Все</a>${artists.map(([a, n]) => `<a class="chip" href="#/catalog/${a}"${cur === a ? ' aria-current="page"' : ""}>${esc(ARTIST[a] || a)} · ${n}</a>`).join("")}</div>
      ${chips("series", facets.series, "Серия")}${chips("country", facets.country, "Страна")}${chips("city", facets.city, "Город")}
      <p class="small" role="status">Показано ${Math.min(catState.take, list.length)} из ${plural(list.length, "листа", "листов", "листов")}.</p>
      <ul class="cwlist">${list.slice(0, catState.take).map(row).join("")}</ul>
      ${!list.length && hasFilter ? `<p class="btn-row"><button type="button" class="btn ghost" id="catReset">Сбросить фильтры</button></p>` : ""}
      ${list.length > catState.take ? `<p class="btn-row"><button type="button" class="btn ghost" id="catMore">Показать ещё</button></p>` : ""}
      ${dock({ href: "#/benoist", t: "Листы Бенуа" }, { href: "#/", t: "Оглавление" })}</div>`;
    document.querySelectorAll(".chips button").forEach((b) => b.addEventListener("click", () => { catState[b.dataset.k] = b.dataset.v; catState.take = 40; viewCatalog(artist); }));
    const more = document.getElementById("catMore"); if (more) more.addEventListener("click", () => { catState.take += 40; viewCatalog(artist); });
    const reset = document.getElementById("catReset"); if (reset) reset.addEventListener("click", () => { catState.series = ""; catState.country = ""; catState.city = ""; catState.take = 40; viewCatalog(artist); });
  }


  // ---------- where it stands, then and now, and where the photographer looked
  const PLAN = { s: 48.815, n: 48.901, w: 2.2365, e: 2.4173 }; // extent of our georeferenced 1878 plan of Paris
  const inPlan = (p) => p && p.lat >= PLAN.s && p.lat <= PLAN.n && p.lon >= PLAN.w && p.lon <= PLAN.e;
  const wedge = (lat, lon, head, len = 150, spread = 22) => {
    const R = 111320, k = Math.cos(lat * Math.PI / 180);
    const pt = (h, d) => [lat + (d * Math.cos(h * Math.PI / 180)) / R, lon + (d * Math.sin(h * Math.PI / 180)) / (R * k)];
    return [[lat, lon], pt(head - spread, len), pt(head, len * 1.06), pt(head + spread, len)];
  };
  const MODE = { exact_verified: "Точное совмещение: контрольные точки проверены.", approximate: "То же место, другой ракурс: перспектива не совпадает. Шторка и «рядом» показывают два целых кадра без наложения.", unverified: "Ракурс не проверен: два отдельных кадра рядом, без подгонки.", lost_or_reconstructed: "Здания или вида больше нет: ниже фото нынешнего места, а не «тот же кадр»." };
  const angleMeta = (q) => { const ph = q.photo || {}; return `<p class="small angmeta"><b>${esc(q.status_ru)}.</b> ${esc(MODE[q.status] || "")}<br>Фото: ${esc(ph.author || "автор не указан")}${ph.date ? ", " + esc(ph.date) : ""}${ph.licence ? ", " + esc(ph.licence) : ", права не указаны"}.${ph.lat != null ? ` Камера: ${Number(ph.lat).toFixed(4)}, ${Number(ph.lon).toFixed(4)}${ph.heading != null ? ", азимут " + Math.round(ph.heading) + "°" : ""}${ph.distance_m != null ? ", ~" + ph.distance_m + " м от здания" : ""}.` : " Положение камеры не указано."}</p>`; };
  function compareSection(e) {
    e = e || { pairs: [] };
    if (!e.pairs.length) {
      return `<h2>Сравнить с сегодняшним днём</h2><div class="lt-tool" role="note"><span class="lt-legend">Современный кадр</span>
        <p>Современный ракурс для этого листа пока не найден: ракурс не установлен. Лист стоит в очереди поиска; пока можно открыть оригинал и место на карте. Мы не подгоняем чужое фото на глаз ради эффекта. Можно <a href="../fieldwork/">снять это место сами</a>: фото останется только у вас в браузере.</p></div>`;
    }
    const q0 = e.pairs[0];
    const picker = e.pairs.length > 1 ? `<div class="angles" role="group" aria-label="Выбрать ракурс"><span class="lt-legend">Выбрать ракурс</span>${e.pairs.map((q, k) => `<button type="button" class="btn ghost angbtn" data-i="${k}" aria-pressed="${k === 0}">${k + 1}. ${esc((q.photo && q.photo.date) || "без даты")}${q.photo && q.photo.author ? " · " + esc(cut(q.photo.author.replace(/ \(.*\)$/, ""), 18)) : ""}</button>`).join("")}</div>` : "";
    return `<h2>Сравнить с сегодняшним днём</h2><div class="cmp" id="cmp" data-n="${e.pairs.length}">${picker}<div id="angmeta">${angleMeta(q0)}</div>
      <iframe class="cmpframe" id="cmpframe" loading="lazy" src="../poc/compare/?embed=1#${esc(q0.id)}" title="Инструмент сравнения: лист и сегодняшний снимок"></iframe>
      <p class="small">Режимы: «Шторка» (два целых кадра, без искажения), «Рядом», «Прозрачность» и «Мерцание A/B» (с пометкой, что перспектива не совпадает). <a id="cmpfull" href="../poc/compare/?journey=1#${esc(q0.id)}">Открыть на весь экран →</a></p></div>`;
  }
  function wireAngles(e) {
    const root = document.getElementById("cmp"); if (!root || !e || e.pairs.length < 2) return;
    root.querySelectorAll(".angbtn").forEach((b) => b.addEventListener("click", () => {
      const q = e.pairs[Number(b.dataset.i)]; if (!q) return;
      root.querySelectorAll(".angbtn").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      document.getElementById("cmpframe").src = `../poc/compare/?embed=1#${q.id}`;
      document.getElementById("cmpfull").href = `../poc/compare/?journey=1#${q.id}`;
      document.getElementById("angmeta").innerHTML = angleMeta(q);
    }));
  }
  // georeferenced atlas sheets of the SODUCO project (Allmaps annotations are read from their repository at the visitor's request;
  // the map images come from the libraries' IIIF servers; we copy neither). Terms of use stay with the sources.
  const SODUCO = [
    { year: 1789, title: "Atlas Verniquet, BnF", annId: "bnf_verniquet_37", url: "https://raw.githubusercontent.com/soduco/allmaps_annotations/main/output/bnf_verniquet/annotation_bnf_verniquet.json" },
    { year: 1836, title: "Atlas Jacoubet, BHVP", annId: "bhvp_jacoubet_32", url: "https://raw.githubusercontent.com/soduco/allmaps_annotations/main/output/bhvp_jacoubet/annotation_bhvp_jacoubet.json" },
    { year: 1868, title: "Atlas municipal, BHdV", annId: "atlas_municipal_1868_bhdv_2", url: "https://raw.githubusercontent.com/soduco/allmaps_annotations/main/output/bhdv_atlas_municipal_1868/annotation_bhdv_atlas_municipal_1868.json" },
    { year: 1888, title: "Atlas municipal, BHdV", annId: "atlas_municipal_1888_bhdv_2", url: "https://raw.githubusercontent.com/soduco/allmaps_annotations/main/output/bhdv_atlas_municipal_1888/annotation_bhdv_atlas_municipal_1888.json" },
    { year: 1900, title: "Atlas municipal, BHdV", annId: "atlas_municipal_1900_bhdv_2", url: "https://raw.githubusercontent.com/soduco/allmaps_annotations/main/output/bhdv_atlas_municipal_1900/annotation_bhdv_atlas_municipal_1900.json" },
  ];
  const CITE = { s: 48.8512, n: 48.8576, w: 2.3418, e: 2.3532 }; // extent of the open Île de la Cité contour layers
  const inCite = (p) => p && p.lat >= CITE.s && p.lat <= CITE.n && p.lon >= CITE.w && p.lon <= CITE.e;
  const gmaps = (p) => `https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lon}`;
  const gstreet = (p) => `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${p.lat},${p.lon}`;
  const gearth = (p) => `https://earth.google.com/web/search/${p.lat},${p.lon}`;
  const inRing = (r, x, y) => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) if ((r[i][1] > y) !== (r[j][1] > y) && x < ((r[j][0] - r[i][0]) * (y - r[i][1])) / (r[j][1] - r[i][1]) + r[i][0]) c = !c; return c; };
  const centroid = (r) => [r.reduce((a, q) => a + q[0], 0) / r.length, r.reduce((a, q) => a + q[1], 0) / r.length];
  const geoCache = {};
  const loadGeo = (k) => geoCache[k] || (geoCache[k] = fetch(`geo/cite-${k}.json`).then((r) => r.json()));
  function mountLayers(map, e) {
    const box = document.querySelector(".layers"); if (!box || !inCite(e.place)) return;
    const yr = document.getElementById("yearRange"), yv = document.getElementById("yearVal"), note = document.getElementById("layNote"), lost = document.getElementById("lostList");
    const grp = { ohm: L.layerGroup(), vas: L.layerGroup(), ign: L.layerGroup() }, on = { ohm: true, vas: false, ign: false };
    const op = (k) => Number(box.querySelector(`.layop[data-k="${k}"]`).value) / 100;
    const style = { ohm: { color: "#355a43", fill: "#355a43" }, vas: { color: "#6b4a8a", fill: "#6b4a8a" }, ign: { color: "#1f4f8a", fill: "#1f4f8a" } };
    let data = {}, modern = [];
    const draw = () => {
      const y = Number(yr.value); yv.textContent = y;
      for (const k of ["ohm", "vas", "ign"]) { grp[k].clearLayers(); if (!on[k] || !data[k]) continue; }
      let shown = 0, gone = [];
      const add = (k, r, extra) => L.polygon(r.map(([x, yy]) => [yy, x]), { weight: 1, color: extra || style[k].color, fillColor: extra || style[k].fill, fillOpacity: op(k) * 0.55, opacity: op(k) }).addTo(grp[k]);
      if (on.ohm && data.ohm) for (const f of data.ohm) {
        if (f.s != null && f.s > y) continue; if (f.e != null && f.e <= y) continue; shown++;
        const [cx, cy] = centroid(f.r), missing = modern.length && !modern.some((m) => cx >= m.b[0] && cx <= m.b[2] && cy >= m.b[1] && cy <= m.b[3] && inRing(m.r, cx, cy));
        add("ohm", f.r, missing ? "#8d4b36" : null).bindTooltip((f.n || "здание") + (f.s ? ", с " + f.s : "") + (missing ? ": сегодня здания на этом месте нет" : ""));
        if (missing && f.n) gone.push(f.n + (f.e ? " (контур до " + f.e + ")" : ""));
      }
      if (on.vas && data.vas) for (const f of data.vas) if (y >= 1810 && y <= 1865) add("vas", f.r);
      if (on.ign && data.ign) for (const f of data.ign) add("ign", f.r);
      note.textContent = on.ohm ? `${plural(shown, "контур", "контура", "контуров")} в ${y} году.` + (on.vas && (y < 1810 || y > 1865) ? " Участки Вассеро показываются только для 1810–1865." : "") : "";
      lost.innerHTML = [...new Set(gone)].slice(0, 12).map((t) => `<li>${esc(t)}</li>`).join("") || "<li>В выбранном году именованных контуров без здания на месте сегодня не найдено.</li>";
    };
    const need = ["ohm", "vasserot", "ign"];
    let loaded = false;
    box.addEventListener("toggle", async () => {
      if (!box.open || loaded) return; loaded = true; note.textContent = "Загружаю контуры…";
      try {
        const [o, v, g] = await Promise.all(need.map(loadGeo));
        data = { ohm: o.features, vas: v.features, ign: g.features };
        modern = g.features.map((f) => ({ r: f.r, b: [Math.min(...f.r.map((q) => q[0])), Math.min(...f.r.map((q) => q[1])), Math.max(...f.r.map((q) => q[0])), Math.max(...f.r.map((q) => q[1]))] }));
        for (const k of ["ohm", "vas", "ign"]) grp[k].addTo(map);
        draw();
      } catch (err) { note.textContent = "Контуры сейчас недоступны."; loaded = false; }
    });
    let warped = null;
    const sel = document.getElementById("oldmapSel"), opr = document.getElementById("oldmapOp"), onote = document.getElementById("oldmapNote");
    sel.addEventListener("change", async () => {
      if (warped) { map.removeLayer(warped); warped = null; }
      if (sel.value === "") { onote.textContent = ""; return; }
      const m = SODUCO[Number(sel.value)]; onote.textContent = "Загружаю привязку карты…";
      try {
        const [{ WarpedMapLayer }, page] = await Promise.all([import("../eras/vendor/allmaps-leaflet-beta55/layer.js"), fetch(m.url).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })]);
        const ann = (page.items || []).find((x) => x.id === m.annId); if (!ann) throw new Error("no annotation");
        const layer = new WarpedMapLayer(undefined, { opacity: Number(opr.value) / 100, zIndex: 250 });
        const res = layer.addGeoreferenceAnnotation(ann);
        if (!res.length || res.every((x) => x instanceof Error)) throw new Error("bad annotation");
        if (Number(sel.value) !== SODUCO.indexOf(m)) return;
        warped = layer; layer.addTo(map);
        onote.textContent = `${m.year}: ${m.title}. Привязка проекта SODUCO (Allmaps), изображение с сервера библиотеки; точность по опорным точкам, не геодезическая. Если карта не появилась, сервер библиотеки сейчас недоступен.`;
      } catch (err) { onote.textContent = "Эту карту сейчас загрузить не удалось (сервер привязки или библиотеки недоступен). Остальные слои работают."; }
    });
    opr.addEventListener("input", () => { if (warped && warped.setOpacity) warped.setOpacity(Number(opr.value) / 100); });
    yr.addEventListener("input", draw);
    box.querySelectorAll(".laychk").forEach((c) => c.addEventListener("change", () => { on[c.dataset.k] = c.checked; draw(); }));
    box.querySelectorAll(".layop").forEach((c) => c.addEventListener("input", draw));
  }
  function placeSection(e) {
    if (!e || !e.place) {
      return `<h2>Где это</h2><div class="lt-tool" role="note"><span class="lt-legend">Место</span><p>Здание на этом листе мы пока не привязали к карте: название не позволяет назвать место без догадок.</p></div>`;
    }
    const plan = inPlan(e.place);
    const est = e.pairs.map((q) => q.artist_estimate).filter(Boolean)[0];
    return `<h2>Где это</h2><p class="small">${esc(e.place.name)}, ${esc(e.place.city)}. Координаты приблизительные (OpenStreetMap).${e.place.href ? ` <a href="${e.place.href}">Весь город на старых и современных картах →</a>` : ""}</p>
      <div id="placemap" class="placemap" role="img" aria-label="Карта: где находится здание и куда смотрит современная фотография"></div>
      <div class="lt-tool placectl"><button type="button" class="btn ghost" id="planBtn" aria-pressed="false"${plan ? "" : " hidden"}>Старый план Парижа 1878</button>
        <label for="planRange" id="planRangeL" hidden><span class="lt-legend">Прозрачность плана</span></label><input id="planRange" type="range" min="10" max="100" value="70" hidden>
        <p class="small" id="planNote" role="status"></p></div>
      ${inCite(e.place) ? `<details class="layers"><summary class="btn ghost">История места по годам: здания, участки, лупа</summary>
        <div class="lt-tool">
          <label for="yearRange"><span class="lt-legend">Эпоха</span> <b id="yearVal">1843</b></label><input id="yearRange" type="range" min="1200" max="2025" step="1" value="1843">
          <p class="small">Показаны контуры, которые на карте существовали в этом году (OpenHistoricalMap; даты вносят волонтёры). <span style="color:#8d4b36">Красным</span>: на месте центра контура сегодня нет здания (по IGN). Это эвристика, не доказательство сноса.</p>
          ${[["ohm", "Здания в выбранный год", 70], ["vas", "Участки Вассеро 1810–1836", 45], ["ign", "Здания сегодня (IGN)", 60]].map(([k, t, v]) => `<div class="layrow"><label><input type="checkbox" class="laychk" data-k="${k}"${k === "ohm" ? " checked" : ""}> ${t}</label><input type="range" class="layop" data-k="${k}" min="10" max="100" value="${v}" aria-label="Прозрачность: ${t}"></div>`).join("")}
          <div class="layrow"><label for="oldmapSel">Старая карта эпохи (Allmaps)</label><select id="oldmapSel"><option value="">нет</option>${SODUCO.map((m, i) => `<option value="${i}">${m.year}: ${esc(m.title)}</option>`).join("")}</select><input type="range" id="oldmapOp" min="10" max="100" value="75" aria-label="Прозрачность старой карты"></div>
          <p class="small" id="oldmapNote" role="status"></p>
          ${inPlan(e.place) ? `<button type="button" class="btn ghost" id="loupeBtn" aria-pressed="false" hidden>Лупа: старый план в круге</button>` : ""}
          <p class="small" id="layNote" role="status"></p>
          <details class="lost"><summary>Что исчезло к сегодняшнему дню</summary><ul id="lostList" class="facts-list"></ul></details>
          <p class="small">Источники: © ALPAGE (ODbL, Arch. nat. F31 73-96 – Arch. Paris), OpenHistoricalMap (CC0), © IGN BD TOPO (Licence Ouverte 2.0).</p>
        </div></details>` : ""}
      <p class="small mapext">Открыть это место: <a href="${esc(gmaps(e.place))}" target="_blank" rel="noopener">Google Карты ↗</a> · <a href="${esc(gstreet(e.place))}" target="_blank" rel="noopener">Street View ↗</a> · <a href="${esc(gearth(e.place))}" target="_blank" rel="noopener">Google Earth ↗</a>. Откроется на сайте Google, наши данные туда не передаются.</p>
      <p class="small">${e.pairs.some((q) => q.photo && q.photo.lat) ? "Зелёный клин: куда смотрит современная фотография (положение камеры из данных Panoramax, направление по компасу снимка)." : "Современной фотографии для этого места пока нет, поэтому направление взгляда не показано."}${est ? " Где стоял художник, известно только как оценка по рисунку: " + esc(est) + "." : " Где стоял художник, мы не знаем: измерить это по рисунку без догадок нельзя."}</p>`;
  }
  let planData = null;
  function mountPlace(e) {
    const el = document.getElementById("placemap");
    if (!e || !e.place || !el || !window.L) return;
    const map = L.map(el, { scrollWheelZoom: false });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
    const pts = [[e.place.lat, e.place.lon]];
    L.circleMarker(pts[0], { radius: 9, color: "#23493d", weight: 2, fillColor: "#8d4b36", fillOpacity: .95 }).addTo(map).bindTooltip(e.place.name);
    for (const q of e.pairs) {
      if (!q.photo || q.photo.lat == null || q.photo.heading == null) continue;
      L.polygon(wedge(q.photo.lat, q.photo.lon, q.photo.heading), { color: "#3d5a45", weight: 1, fillColor: "#3d5a45", fillOpacity: .35 }).addTo(map)
        .bindTooltip("Фото " + (q.photo.date || "") + ", направление " + Math.round(q.photo.heading) + "°");
      L.circleMarker([q.photo.lat, q.photo.lon], { radius: 5, color: "#3d5a45", fillColor: "#fbf5e4", fillOpacity: 1 }).addTo(map);
      pts.push([q.photo.lat, q.photo.lon]);
    }
    if (pts.length > 1) map.fitBounds(pts, { padding: [30, 30], maxZoom: 17 }); else map.setView(pts[0], 16);
    mountLayers(map, e);
    const btn = document.getElementById("planBtn"), range = document.getElementById("planRange"), rl = document.getElementById("planRangeL"), note = document.getElementById("planNote");
    if (!btn || btn.hidden) return;
    let layer = null;
    const localPlan = (data) => new (L.Layer.extend({
      onAdd(m) {
        this.image = document.createElement("img"); this.image.src = "../eras/img/loc-2012586603-paris-1878.jpg"; this.image.alt = ""; this.image.className = "planimg";
        this.image.style.clipPath = `polygon(${data.clip})`; this.image.style.opacity = String(range.value / 100);
        this.update = () => {
          const [tl, tr, , bl] = data.corners.map((c) => m.latLngToLayerPoint(c));
          this.m = [(tr.x - tl.x) / 2000, (tr.y - tl.y) / 2000, (bl.x - tl.x) / 1448, (bl.y - tl.y) / 1448, tl.x, tl.y];
          this.image.style.transform = `matrix(${this.m.join(",")})`;
          if (this.loupeAt) this.maskAt(this.loupeAt);
        };
        m.getPane("overlayPane").append(this.image); m.on("move zoom viewreset", this.update); this.update();
      },
      maskAt(pt) { // circular window onto the old plan; the radius is 90 screen pixels whatever the plan scale
        const [a, b2, c, d, e0, f0] = this.m, det = a * d - b2 * c; if (!det) return;
        const u = (d * (pt.x - e0) - c * (pt.y - f0)) / det, v = (-b2 * (pt.x - e0) + a * (pt.y - f0)) / det, r = 90 / Math.sqrt(Math.abs(det));
        const g = `radial-gradient(circle ${r}px at ${u}px ${v}px, #000 94%, transparent 100%)`;
        this.image.style.webkitMaskImage = g; this.image.style.maskImage = g;
      },
      setLoupe(on) { this.loupeAt = on ? this.loupeAt || map.latLngToLayerPoint(map.getCenter()) : null; if (!on) { this.image.style.webkitMaskImage = this.image.style.maskImage = "none"; } else this.maskAt(this.loupeAt); },
      onRemove(m) { this.image.remove(); m.off("move zoom viewreset", this.update); },
    }))();
    btn.addEventListener("click", async () => {
      const on = btn.getAttribute("aria-pressed") !== "true";
      btn.setAttribute("aria-pressed", String(on)); range.hidden = rl.hidden = !on;
      if (!on) { if (layer) map.removeLayer(layer); note.textContent = ""; return; }
      try {
        if (!planData) planData = await (await fetch("../eras/data/paris-1878-overlay.json")).json();
        layer = layer || localPlan(planData); layer.addTo(map);
        note.textContent = "План Парижа 1878 года (Библиотека Конгресса), приблизительная привязка по 15 точкам; участок плана ограничен опорными точками, дальше карта сегодняшняя.";
      } catch (err) { note.textContent = "План сейчас недоступен."; btn.setAttribute("aria-pressed", "false"); }
    });
    range.addEventListener("input", () => { if (layer && layer.image) layer.image.style.opacity = String(range.value / 100); });
    const lb = document.getElementById("loupeBtn");
    if (lb) {
      const move = (ev) => { if (layer && layer.loupeAt) { layer.loupeAt = map.mouseEventToLayerPoint(ev.touches ? ev.touches[0] : ev); layer.maskAt(layer.loupeAt); } };
      lb.hidden = false;
      lb.addEventListener("click", () => {
        if (!layer || !map.hasLayer(layer)) { note.textContent = "Сначала включите «Старый план Парижа 1878» выше."; return; }
        const on = lb.getAttribute("aria-pressed") !== "true"; lb.setAttribute("aria-pressed", String(on));
        if (on) { map.dragging.disable(); range.value = 100; layer.image.style.opacity = "1"; } else map.dragging.enable();
        layer.setLoupe(on);
      });
      el.addEventListener("mousemove", move); el.addEventListener("touchstart", move, { passive: true }); el.addEventListener("touchmove", move, { passive: true });
    }
  }

  // ---------- the story of a place: every statement points to its source, unknowns are said aloud
  const STATUS = { exists: "здание стоит", rebuilt: "здание пережило пожар и восстановлено", lost: "здание утрачено" };
  const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return ""; } };
  function viewPlace(id) {
    const pl = D.places.find((x) => x.id === id);
    if (!pl) return notFound();
    setTitle(pl.name_ru); crumbs([{ t: "Книга", href: "#/" }, { t: "Истории мест", href: "#/places" }, { t: pl.name_ru }]);
    const i = D.places.indexOf(pl), next = D.places[i + 1], prev = D.places[i - 1];
    const sheets = pl.related_sheet_ids.map((sid) => D.sheets.find((x) => x.id === sid)).filter(Boolean);
    const entries = sheets.map((x) => D.sp[x.id]).filter(Boolean);
    const hasGeo = Number.isFinite(Number(pl.lat)) && Number.isFinite(Number(pl.lon));
    const placeEntry = hasGeo || entries.length ? { place: { name: pl.name_ru, city: "Париж", lat: Number(pl.lat), lon: Number(pl.lon) }, pairs: entries.flatMap((x) => x.pairs).filter((q, k, a) => a.findIndex((z) => z.id === q.id) === k), href: null } : null;
    const compareHtml = placeEntry ? compareSection(placeEntry) : "";
    const mapHtml = placeEntry && hasGeo ? placeSection(placeEntry) : "";
    const lostNote = pl.status === "lost" ? `<div class="lt-tool" role="note"><span class="lt-legend">Сравнение с фото</span><p>Здания больше нет, поэтому «того же кадра» сегодня не существует. Мы не подгоняем чужой фасад под этот лист: показываем лист и то, что теперь на этом месте.</p></div>` : "";
    $app.innerHTML = `<div class="page-enter">
      <section class="chead"><p class="eyebrow">История места · ${esc(STATUS[pl.status] || "")}</p><h1>${esc(pl.name_ru)}</h1><p class="lede">${esc(pl.lede_ru)}</p></section>
      ${lostNote}
      ${compareHtml}
      ${sheets.length ? `<h2>Листы с этим местом</h2><div class="plates">${sheets.map((x) => `<a class="pl" href="#/sheet/${esc(x.id)}"><img src="${esc(x.image)}" alt="" loading="lazy" width="400"><span class="t">${esc(cut(x.title.split(" / ")[0], 40))}</span><span class="s">${esc(x.holder)}</span></a>`).join("")}</div>` : ""}
      <h2>Что известно</h2>
      <ol class="story">${pl.facts.map((f) => `<li><span class="when">${esc(f.date)}</span><p>${esc(f.text_ru)}</p><a class="src" href="${esc(safe(f.source_url))}" target="_blank" rel="noopener">${esc(f.source_name || host(f.source_url))} ↗</a></li>`).join("")}</ol>
      ${pl.changes_ru && pl.changes_ru.length ? `<h2>Что изменилось</h2><ul class="facts-list">${pl.changes_ru.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : ""}
      ${mapHtml}
      ${pl.old_plan ? `<h2>Старый план</h2><p>${esc(pl.old_plan.note)} <a href="../eras/">Открыть карту эпох →</a> Слой «Старый план Парижа 1878» включается на карте выше.</p>` : ""}
      ${pl.unknowns_ru && pl.unknowns_ru.length ? `<h2>Не установлено</h2><ul class="facts-list unk">${pl.unknowns_ru.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : ""}
      <p class="small">${esc(pl.print_licence_note || "")}</p>
      ${dock(next ? { href: "#/place/" + next.id, t: next.name_ru, small: "Следующее место" } : { href: "#/places", t: "Все места" }, prev ? { href: "#/place/" + prev.id, t: prev.name_ru } : { href: "#/places", t: "Истории мест" })}</div>`;
    if (placeEntry && hasGeo) mountPlace(placeEntry);
    if (placeEntry) wireAngles(placeEntry);
  }
  function viewPlaces() {
    setTitle("Истории мест"); crumbs([{ t: "Книга", href: "#/" }, { t: "Истории мест" }]);
    const geoPlaces = D.places.filter((p) => Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lon))).map((p) => ({ title: p.name_ru, lat: Number(p.lat), lon: Number(p.lon), href: `#/place/${encodeURIComponent(p.id)}`, cta: "Открыть историю →" }));
    $app.innerHTML = `<div class="page-enter"><section class="chead"><p class="eyebrow">Здания на листах</p><h1>Истории мест</h1><p class="lede">Что стояло на листе, что с этим стало и откуда мы это знаем. Каждый факт ведёт к источнику.</p></section>
      <ol class="toc">${D.places.map((p) => `<li><a href="#/place/${esc(p.id)}"><span class="nm">${esc(p.name_ru)}</span><span class="num">${plural(p.facts.length, "факт", "факта", "фактов")}</span><span class="sub">${esc(STATUS[p.status] || "")}</span></a></li>`).join("")}</ol>
      ${geoPlaces.length ? `<h2>На карте Парижа</h2><div class="lmap" id="lmap" role="region" aria-label="Карта: исторические места"></div><p class="small">Нажмите метку, чтобы открыть историю здания.</p>` : ""}
      ${dock({ href: "#/benoist", t: "Листы Бенуа" }, { href: "#/", t: "Оглавление" })}</div>`;
    if (geoPlaces.length) mountMap("lmap", geoPlaces, null);
  }

  // ---------- chronology: slide through the years the register knows (only works whose record states a year)
  const TL = { from: 1840, to: 1865, take: 40 };
  const TL_MIN = 1790, TL_MAX = 1890;
  function viewTimeline() {
    setTitle("Хронология"); crumbs([{ t: "Книга", href: "#/" }, { t: "Хронология" }]);
    const R = D.reg || { works: [] };
    const dated = R.works.filter((w) => w.year);
    if (!dated.length) return notFound();
    const byImg = new Map(D.sheets.map((x) => [x.image, x]));
    const inScale = dated.filter((w) => w.year >= TL_MIN && w.year <= TL_MAX);
    const decades = []; for (let d = TL_MIN; d < TL_MAX; d += 10) decades.push([d, inScale.filter((w) => w.year >= d && w.year < d + 10).length]);
    const peak = Math.max(1, ...decades.map((x) => x[1]));
    const draw = () => {
      const lo = Math.min(TL.from, TL.to), hi = Math.max(TL.from, TL.to);
      const list = inScale.filter((w) => w.year >= lo && w.year <= hi).sort((a, b) => a.year - b.year);
      const withImg = list.filter((w) => w.image).length;
      document.getElementById("tlOut").innerHTML = `<p class="small" role="status">${lo === hi ? lo : lo + "–" + hi}: ${plural(list.length, "лист", "листа", "листов")}, из них ${withImg} с картинкой в книге. Без указанного года в записях ещё ${R.works.length - dated.length} листов, вне шкалы ${dated.length - inScale.length}.</p>
        <ul class="cwlist">${list.slice(0, TL.take).map((w) => `<li class="tlyear" aria-hidden="true">${w.year}</li>` + workRow(w, byImg)).join("")}</ul>
        ${list.length > TL.take ? `<p class="btn-row"><button type="button" class="btn ghost" id="tlMore">Показать ещё</button></p>` : ""}`;
      const more = document.getElementById("tlMore"); if (more) more.addEventListener("click", () => { TL.take += 40; draw(); });
      document.querySelectorAll(".tlbar").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.d) <= hi && Number(b.dataset.d) + 9 >= lo)));
      document.getElementById("tlFromV").textContent = TL.from; document.getElementById("tlToV").textContent = TL.to;
    };
    $app.innerHTML = `<div class="page-enter">
      <section class="chead"><p class="eyebrow">Листы по годам</p><h1>Хронология</h1>
        <p class="lede">Двигайте ползунки: книга покажет листы, у которых музей назвал год. Остальные записи без года в эту шкалу не попадают, мы их не угадываем.</p></section>
      <div class="tlhist" role="group" aria-label="Сколько листов в каждом десятилетии">${decades.map(([d, n]) => `<button type="button" class="tlbar" data-d="${d}" aria-label="${d}-е годы: ${n}"><i style="height:${Math.round((n / peak) * 100)}%"></i><span>${d}</span><b>${n}</b></button>`).join("")}</div>
      <div class="lt-tool tlctl"><label for="tlFrom"><span class="lt-legend">С года</span> <b id="tlFromV">${TL.from}</b></label><input id="tlFrom" type="range" min="${TL_MIN}" max="${TL_MAX}" step="1" value="${TL.from}">
        <label for="tlTo"><span class="lt-legend">По год</span> <b id="tlToV">${TL.to}</b></label><input id="tlTo" type="range" min="${TL_MIN}" max="${TL_MAX}" step="1" value="${TL.to}"></div>
      <div id="tlOut"></div>
      ${dock({ href: "#/catalog", t: "Собрание" }, { href: "#/", t: "Оглавление" })}</div>`;
    const set = (k, v) => { TL[k] = Number(v); TL.take = 40; draw(); };
    document.getElementById("tlFrom").addEventListener("input", (e) => set("from", e.target.value));
    document.getElementById("tlTo").addEventListener("input", (e) => set("to", e.target.value));
    document.querySelectorAll(".tlbar").forEach((b) => b.addEventListener("click", () => {
      const d = Number(b.dataset.d); TL.from = d; TL.to = d + 9; TL.take = 40;
      document.getElementById("tlFrom").value = d; document.getElementById("tlTo").value = d + 9; draw();
    }));
    draw();
  }

  // ---------- one register entry (also for works we may not copy): everything we know, and a way to keep exploring
  function viewWork(id) {
    const w = (D.reg.works || []).find((x) => x.id === id);
    if (!w) return notFound();
    const sh = w.image && D.sheets.find((x) => x.image === w.image);
    const title = String(w.title || "Без названия").split(" / ")[0];
    setTitle(title); crumbs([{ t: "Книга", href: "#/" }, { t: "Собрание", href: "#/catalog" }, { t: cut(title, 28) }]);
    const same = (D.reg.works || []).filter((x) => x.id !== w.id && ((w.series && x.series === w.series) || (w.city && x.city === w.city)) && x.artist === w.artist).slice(0, 8);
    $app.innerHTML = `<div class="page-enter">
      <section class="chead"><p class="eyebrow">${esc(ARTIST[w.artist] || w.artist)}${w.series ? " · " + esc(w.series) : ""}</p><h1>${esc(title)}</h1></section>
      ${sh ? `<p class="btn-row"><a class="btn" href="#/sheet/${esc(sh.id)}">Открыть лист крупно, сравнить и найти на карте →</a></p>` : `<div class="lt-tool" role="note"><span class="lt-legend">Изображения нет у нас</span><p>${w.open_file ? "Файл открыт у хранителя, но мы его ещё не загрузили." : "Права на показ этого листа у хранителя не подтверждены, поэтому мы не копируем его: он остаётся ссылкой на музей."} Ниже всё, что известно о листе, и похожие работы, которые можно открыть у нас.</p></div>`}
      <h2>Что известно</h2><dl class="facts"><dt>Автор</dt><dd>${esc(ARTIST[w.artist] || w.artist)}${w.artist === "uncertain-benoist" ? " (в записи названа только фамилия или оба брата)" : ""}</dd>
        ${w.series ? `<dt>Серия</dt><dd>${esc(w.series)}</dd>` : ""}${w.city ? `<dt>Место</dt><dd>${esc(w.city)}${w.country ? ", " + esc(w.country) : ""}</dd>` : ""}
        <dt>Год</dt><dd>${w.year ? esc(String(w.year)) + (w.date && w.date !== String(w.year) ? " (в записи: " + esc(w.date) + ")" : "") : "в записях не указан"}</dd>
        <dt>Вид</dt><dd>${esc({ print: "лист", drawing: "рисунок", book: "книга или том", page_in_book: "пластина из книги", volume: "том" }[w.kind] || w.kind || "не указан")}</dd>
        <dt>Экземпляры</dt><dd>${w.impressions > 1 ? plural(w.impressions, "запись", "записи", "записей") + " о том же листе в разных каталогах" : "одна запись"}</dd></dl>
      ${(w.links || []).length ? `<h2>У хранителей</h2><ul class="facts-list">${w.links.map((l) => `<li><a href="${esc(safe(l.u))}" target="_blank" rel="noopener">${esc(l.i || "запись в каталоге")} ↗</a></li>`).join("")}</ul>` : ""}
      ${same.length ? `<h2>Другие листы ${w.series ? "серии" : "из этого места"}</h2><ul class="cwlist">${same.map((x) => workRow(x, new Map(D.sheets.map((y) => [y.image, y])))).join("")}</ul>` : ""}
      ${dock({ href: "#/catalog", t: "Собрание" }, { href: "#/timeline", t: "Хронология" })}</div>`;
  }

  function notFound() {
    setTitle("Страница не найдена"); crumbs([{ t: "Книга", href: "#/" }, { t: "Нет такой страницы" }]);
    $app.innerHTML = `<section class="chead"><h1>Такой страницы нет</h1><p class="lede">Возможно, ссылка устарела. Вернитесь к оглавлению.</p><div class="btn-row"><a class="btn" href="#/">К оглавлению</a></div></section>`;
  }

  // ---------- maps (Leaflet is vendored; tiles come from OSM like everywhere else in the museum)
  function mountMap(elId, pts, focus) {
    const el = document.getElementById(elId); if (!el || !window.L || !pts.length) return;
    const map = L.map(el, { scrollWheelZoom: false, zoomControl: true });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
    const group = [];
    for (const p of pts) {
      const m = L.circleMarker([p.lat, p.lon], { radius: focus ? 9 : 7, color: "#23493d", weight: 2, fillColor: focus ? "#8d4b36" : "#c9a96e", fillOpacity: .95 }).addTo(map);
      if (!focus) m.bindPopup(`<b>${esc(p.title)}</b><br><a href="${p.href || plateLink(p)}">${esc(p.cta || "Открыть лист →")}</a>`);
      group.push([p.lat, p.lon]);
    }
    if (focus) map.setView(group[0], 16); else map.fitBounds(group, { padding: [24, 24], maxZoom: 15 });
  }


  // deep zoom with OpenSeadragon (BSD-3-Clause, eras/vendor/openseadragon-6.1.1): pinch, double tap, wheel, keys; the image file is never changed
  let osdLoad = null;
  const loadOsd = () => osdLoad || (osdLoad = new Promise((res, rej) => {
    if (window.OpenSeadragon) return res(window.OpenSeadragon);
    const sc = document.createElement("script"); sc.src = "../eras/vendor/openseadragon-6.1.1/openseadragon.min.js";
    sc.onload = () => res(window.OpenSeadragon); sc.onerror = () => { osdLoad = null; rej(new Error("osd")); }; document.head.append(sc);
  }));
  function wireDeepZoom(url, label) {
    const btn = document.getElementById("deepBtn"), wrap = document.getElementById("zoomwrap"), ctl = document.querySelector(".zoomctl"); if (!btn || !wrap) return;
    let viewer = null; const keep = document.getElementById("zoomimg"); // the same element comes back, so the lens and slider keep working
    const restore = () => { wrap.innerHTML = ""; wrap.append(keep); wrap.classList.remove("deep"); ctl.hidden = false; btn.setAttribute("aria-pressed", "false"); document.getElementById("deepCtl").hidden = true; };
    btn.addEventListener("click", async () => {
      if (viewer) { viewer.destroy(); viewer = null; restore(); return; }
      btn.disabled = true;
      try {
        const OSD = await loadOsd(); wrap.innerHTML = ""; wrap.classList.add("deep"); ctl.hidden = true;
        viewer = OSD({ element: wrap, showNavigationControl: false, drawer: "canvas", placeholderFillStyle: "#eae3d1", visibilityRatio: 1, maxZoomPixelRatio: 3, gestureSettingsTouch: { pinchToZoom: true, clickToZoom: false, dblClickToZoom: true }, tileSources: { type: "image", url } });
        viewer.addHandler("open-failed", () => { if (viewer) { viewer.destroy(); viewer = null; } restore(); document.getElementById("deepNote").textContent = "Не удалось открыть просмотр вблизи; рассмотрите лист ползунком."; });
        document.getElementById("deepCtl").hidden = false; btn.setAttribute("aria-pressed", "true");
        const z = (f) => { viewer.viewport.zoomBy(f); viewer.viewport.applyConstraints(); };
        document.getElementById("deepIn").onclick = () => z(1.5); document.getElementById("deepOut").onclick = () => z(1 / 1.5); document.getElementById("deepHome").onclick = () => viewer.viewport.goHome();
        window.__osd = viewer;
      } catch (e) { restore(); document.getElementById("deepNote").textContent = "Просмотр вблизи сейчас недоступен: рассмотрите лист ползунком ниже."; }
      finally { btn.disabled = false; }
    });
  }
  const deepControls = '<div class="lt-tool deepctl"><button type="button" class="btn ghost" id="deepBtn" aria-pressed="false">Смотреть вблизи: щипок и двойное касание</button><span id="deepCtl" hidden><button type="button" class="btn ghost" id="deepIn" aria-label="Приблизить">+</button><button type="button" class="btn ghost" id="deepOut" aria-label="Отдалить">−</button><button type="button" class="btn ghost" id="deepHome">Весь лист</button></span><p class="small" id="deepNote" role="status">Файл не меняется; приближение только на экране.</p></div>';
  // ---------- exhibitions and the historical album reader (rights come from the museums' own open-data feeds)
  const lazyJson = {};
  const getJson = (u) => lazyJson[u] || (lazyJson[u] = fetch(u).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }));
  const exCap = (w) => `<figcaption class="excap"><b>${esc(w.title)}</b><span>${esc(w.artist)}${w.role ? ", " + esc(w.role) : ""}${w.date ? " · " + esc(w.date) : ""}${w.technique ? " · " + esc(cut(w.technique, 60)) : ""}</span><span class="small">${esc(w.credit)} · <a href="${esc(safe(w.record_url))}" target="_blank" rel="noopener">запись музея ↗</a></span></figcaption>`;
  async function viewExhibitions() {
    setTitle("Выставки"); crumbs([{ t: "Книга", href: "#/" }, { t: "Выставки" }]);
    let X; try { X = await getJson("exhibitions.json"); } catch (e) { return notFound(); }
    $app.innerHTML = `<div class="page-enter"><section class="chead"><p class="eyebrow">Залы музея</p><h1>Выставки</h1><p class="lede">Большие темы вокруг наследия Бенуа: Рим, Венеция, исчезнувший Париж. Работы других мастеров открыты музеями, права и источник указаны у каждой.</p></section>
      <div class="exlist">${X.exhibitions.map((e) => `<a class="exhall" href="#/exhibit/${esc(e.id)}"><img src="${esc(e.works[0].image)}" alt="" loading="lazy"><span class="cap"><span class="where">${esc(e.city)} · ${plural(e.works.length, "работа", "работы", "работ")}</span><b>${esc(e.title)}</b><span class="hook">${esc(e.lede)}</span></span></a>`).join("")}</div>
      <p class="small">Правила: рисунки и гравюры берутся только там, где музей сам указал свободное использование; подпись составляется из записи музея, без домыслов. Работы Бенуа и других художников из книги не смешиваются: у каждого свои роли.</p>
      ${dock({ href: "#/albums", t: "Альбомы" }, { href: "#/", t: "Оглавление" })}</div>`;
  }
  async function viewExhibit(id) {
    let X; try { X = await getJson("exhibitions.json"); } catch (e) { return notFound(); }
    const ex = X.exhibitions.find((e) => e.id === id); if (!ex) return notFound();
    setTitle(ex.title); crumbs([{ t: "Книга", href: "#/" }, { t: "Выставки", href: "#/exhibitions" }, { t: ex.title }]);
    const ws = ex.works, fig = (w, cls = "") => `<figure class="exfig ${cls}"><a class="eximg" href="#/exwork/${esc(w.id)}"><img src="${esc(w.image)}" alt="${esc(w.title)}" loading="lazy" width="${w.w}" height="${w.h}"></a>${exCap(w)}</figure>`;
    const parts = []; let i = 1; const rest = ws.slice(1, ws.length - 6 > 1 ? ws.length - 6 : ws.length);
    let k = 0;
    while (k < rest.length) {
      const a = rest[k], b = rest[k + 1], kind = k % 5;
      if (kind === 2 || !b) { parts.push(`<section class="spread full"><p class="eyebrow">Полноэкранное произведение</p>${fig(a)}</section>`); k += 1; }
      else { const dialog = a.artist !== b.artist; parts.push(`<section class="spread pair"><p class="eyebrow">${dialog ? "Диалог: " + esc(a.artist) + " и " + esc(b.artist) : "Две связанные работы"}</p><div class="pairgrid">${fig(a)}${fig(b)}</div></section>`); k += 2; }
      i++;
    }
    const tail = ws.slice(rest.length + 1);
    $app.innerHTML = `<div class="page-enter exhibit"><section class="spread hero">${fig(ws[0], "heroimg")}<div class="herotext"><p class="eyebrow">${esc(ex.city)}</p><h1>${esc(ex.title)}</h1><p class="lede">${esc(ex.lede)}</p><p class="small">${plural(ws.length, "работа", "работы", "работ")} · ${[...new Set(ws.map((w) => w.artist))].map(esc).join(", ")}</p></div></section>
      ${parts.join("")}
      ${tail.length ? `<section class="spread mosaic"><p class="eyebrow">Музейная галерея</p><div class="mosaicgrid">${tail.map((w) => `<a class="mtile" href="#/exwork/${esc(w.id)}"><img src="${esc(w.image)}" alt="${esc(w.title)}" loading="lazy"><span>${esc(cut(w.title, 46))}</span></a>`).join("")}</div></section>` : ""}
      <p class="small">Все работы открыты музеями (Метрополитен, Национальная галерея искусства, Институт искусств Чикаго, Кливленд, Рейксмюзеум); условия указаны под каждой работой.</p>
      ${dock({ href: "#/exhibitions", t: "Все выставки" }, { href: "#/", t: "Оглавление" })}</div>`;
  }
  async function viewExWork(id) {
    let X; try { X = await getJson("exhibitions.json"); } catch (e) { return notFound(); }
    let ex, w; for (const e of X.exhibitions) { const f = e.works.find((x) => x.id === id); if (f) { ex = e; w = f; } }
    if (!w) return notFound();
    setTitle(w.title); crumbs([{ t: "Книга", href: "#/" }, { t: "Выставки", href: "#/exhibitions" }, { t: ex.title, href: "#/exhibit/" + ex.id }, { t: cut(w.title, 28) }]);
    const i = ex.works.indexOf(w), nx = ex.works[i + 1], pv = ex.works[i - 1];
    $app.innerHTML = `<div class="page-enter plate"><section class="chead"><p class="eyebrow">${esc(ex.title)} · ${i + 1} из ${ex.works.length}</p><h1>${esc(w.title)}</h1></section>
      <figure class="lt-sheet"><div class="zoomwrap" id="zoomwrap" tabindex="0" aria-label="Работа крупно. Прокручивайте, чтобы рассмотреть детали"><img id="zoomimg" src="${esc(w.image)}" alt="${esc(w.title)}" width="${w.w}"></div>
        <div class="lt-tool zoomctl"><label for="zoomrange"><span class="lt-legend">Увеличение</span> <b id="zoomval">100%</b></label><input id="zoomrange" type="range" min="100" max="300" step="10" value="100"></div>
        ${deepControls}
        <figcaption class="lt-imprint"><span class="l">${esc(w.institution)}</span><span class="c">${esc(cut(w.rights, 60))}</span><span class="r">${esc(w.accession)}</span></figcaption></figure>
      <dl class="facts"><dt>Автор</dt><dd>${esc(w.artist)}${w.role ? ", " + esc(w.role) : ""}</dd><dt>Дата</dt><dd>${esc(w.date || "в записи не указана")}</dd><dt>Техника</dt><dd>${esc(w.technique || "в записи не указана")}</dd>${w.series ? `<dt>Серия</dt><dd>${esc(w.series)}</dd>` : ""}<dt>Музей</dt><dd>${esc(w.institution)}, ${esc(w.accession)}</dd><dt>Права</dt><dd>${esc(w.rights)}</dd><dt>Оригинал</dt><dd><a href="${esc(safe(w.record_url))}" target="_blank" rel="noopener">запись в музее ↗</a></dd></dl>
      ${dock(nx ? { href: "#/exwork/" + nx.id, t: cut(nx.title, 26), small: "Дальше" } : { href: "#/exhibit/" + ex.id, t: "К выставке" }, pv ? { href: "#/exwork/" + pv.id, t: cut(pv.title, 22) } : { href: "#/exhibit/" + ex.id, t: "К выставке" })}</div>`;
    const range = document.getElementById("zoomrange"), im = document.getElementById("zoomimg"), val = document.getElementById("zoomval");
    range.addEventListener("input", () => { im.style.width = range.value + "%"; val.textContent = range.value + "%"; });
    wireDeepZoom(w.image, w.title);
  }
  async function viewAlbums() {
    setTitle("Исторические альбомы"); crumbs([{ t: "Книга", href: "#/" }, { t: "Альбомы" }]);
    let A; try { A = await getJson("albums/paris-dans-sa-splendeur.json"); } catch (e) { return notFound(); }
    $app.innerHTML = `<div class="page-enter"><section class="chead"><p class="eyebrow">Книги целиком</p><h1>Исторические альбомы</h1><p class="lede">Листы в том порядке, в каком их напечатали, а не в нашей подборке. Каждый лист ведёт к странице библиотеки.</p></section>
      <a class="exhall" href="#/album/${esc(A.id)}/0"><img src="${esc(A.covers[0].image)}" alt="" loading="lazy"><span class="cap"><span class="where">${esc(A.years)} · ${esc(A.publisher)}</span><b>${esc(A.title)}</b><span class="hook">${plural(A.plates.length, "планша", "планши", "планш")} из изданий в оцифровке ${esc(A.holder)}. Порядок: ${esc(A.order_basis)}</span></span></a>
      <div class="lt-tool" role="note"><span class="lt-legend">Что ещё готовится</span><p>«La Bretagne contemporaine» (BnF), «Rome dans sa grandeur» и «Vues de Paris»: оригинальный порядок листов пока не подтверждён первичными каталогами. Пока они не открыты как альбомы, чтобы не выдать нашу подборку за порядок издания.</p></div>
      ${dock({ href: "#/exhibitions", t: "Выставки" }, { href: "#/", t: "Оглавление" })}</div>`;
  }
  async function viewAlbum(id, nStr) {
    let A; try { A = await getJson("albums/paris-dans-sa-splendeur.json"); } catch (e) { return notFound(); }
    if (id !== A.id) return notFound();
    const n = Math.max(0, Math.min(A.plates.length, Number(nStr) || 0)), total = A.plates.length;
    setTitle(A.title); crumbs([{ t: "Книга", href: "#/" }, { t: "Альбомы", href: "#/albums" }, { t: A.title }]);
    const go = (k) => `#/album/${esc(A.id)}/${k}`;
    const p = n ? A.plates[n - 1] : null;
    const body = !p ? `<section class="spread albumcover"><p class="eyebrow">Обложка и титул</p><div class="coverrow">${A.covers.map((c) => `<figure class="exfig"><img src="${esc(c.image)}" alt="${esc(c.title)}" loading="lazy" width="${c.w}" height="${c.h}"><figcaption class="excap"><b>${esc(c.title)}</b><span class="small"><a href="${esc(safe(c.record_url))}" target="_blank" rel="noopener">страница библиотеки ↗</a></span></figcaption></figure>`).join("")}</div>
        <p>${esc(A.full_title)}. ${esc(A.publisher)}, ${esc(A.years)}.</p><p class="small">${esc(A.attribution_note)}</p><p class="small">${esc(A.coverage.note)} ${esc(A.order_basis)}</p>
        <p class="btn-row"><a class="btn" href="${go(1)}">Открыть первую планшу →</a></p></section>`
      : `<section class="spread albumplate"><figure class="lt-sheet"><div class="zoomwrap" id="zoomwrap" tabindex="0" aria-label="Планша крупно. Прокручивайте, чтобы рассмотреть детали"><img id="zoomimg" src="${esc(p.image)}" alt="${esc(p.title)}" width="${p.w}"></div>
        <div class="lt-tool zoomctl"><label for="zoomrange"><span class="lt-legend">Увеличение</span> <b id="zoomval">100%</b></label><input id="zoomrange" type="range" min="100" max="300" step="10" value="100"></div>
        <figcaption class="lt-imprint"><span class="l">Том ${p.volume}</span><span class="c">${esc(p.rights)}</span><span class="r">${esc(A.years)}</span></figcaption></figure>
        <p class="small">Подпись, название и имя художника напечатаны на самой планше: приблизьте её. Библиотека автора отдельной планши не называет. <a href="${esc(safe(p.record_url))}" target="_blank" rel="noopener">Страница библиотеки ↗</a></p></section>`;
    $app.innerHTML = `<div class="page-enter albumview"><section class="chead"><p class="eyebrow">${esc(A.title)} · ${esc(A.years)}</p><h1>${p ? esc(p.title) + " из " + total : "Альбом"}</h1></section>${body}
      <div class="lt-tool albumnav"><label for="albumRange"><span class="lt-legend">Планша</span> <b id="albumVal">${n || "обложка"}</b></label><input id="albumRange" type="range" min="0" max="${total}" value="${n}" aria-label="Номер планши"></div>
      <div class="thumbrail" role="list" aria-label="Все планши">${A.plates.map((q, i) => `<a role="listitem" class="th2" href="${go(i + 1)}"${i + 1 === n ? ' aria-current="true"' : ""}><img src="${esc(q.image)}" alt="${esc(q.title)}" loading="lazy" width="80"><span>${q.n}${q.bis ? "b" : ""}</span></a>`).join("")}</div>
      ${dock(n < total ? { href: go(n + 1), t: n ? "Планша " + (n + 1) : "Первая планша", small: "Дальше" } : { href: "#/albums", t: "Все альбомы" }, n > 0 ? { href: go(n - 1), t: n > 1 ? "Планша " + (n - 1) : "Обложка" } : { href: "#/albums", t: "Альбомы" })}</div>`;
    const rail = document.querySelector(".thumbrail [aria-current]"); if (rail && rail.scrollIntoView) rail.scrollIntoView({ inline: "center", block: "nearest" });
    const rg = document.getElementById("albumRange"); rg.addEventListener("change", () => { location.hash = go(Number(rg.value)); });
    if (p) { const range = document.getElementById("zoomrange"), im = document.getElementById("zoomimg"), val = document.getElementById("zoomval"); range.addEventListener("input", () => { im.style.width = range.value + "%"; val.textContent = range.value + "%"; }); }
    window.__albumKey && document.removeEventListener("keydown", window.__albumKey);
    window.__albumKey = (e) => { if (!/^#\/album\//.test(location.hash) || /INPUT|SELECT|TEXTAREA/.test((e.target || {}).tagName || "")) return; if (e.key === "ArrowRight" && n < total) location.hash = go(n + 1); if (e.key === "ArrowLeft" && n > 0) location.hash = go(n - 1); };
    document.addEventListener("keydown", window.__albumKey);
  }

  // ---------- router
  function route() {
    if (!D) return;
    const h = location.hash.replace(/^#\/?/, "").split("/");
    const arg = decodeURIComponent(h.slice(1).join("/"));
    if (h[0] === "country") viewCountry(arg);
    else if (h[0] === "city") viewCity(arg);
    else if (h[0] === "plate") viewPlate(arg);
    else if (h[0] === "benoist") viewBenoist();
    else if (h[0] === "sheet") viewSheet(arg);
    else if (h[0] === "place") viewPlace(arg);
    else if (h[0] === "places") viewPlaces();
    else if (h[0] === "catalog") viewCatalog(arg);
    else if (h[0] === "timeline") viewTimeline();
    else if (h[0] === "exhibitions") viewExhibitions();
    else if (h[0] === "exhibit") viewExhibit(arg);
    else if (h[0] === "exwork") viewExWork(arg);
    else if (h[0] === "albums") viewAlbums();
    else if (h[0] === "album") viewAlbum(h[1], h[2]);
    else if (h[0] === "work") viewWork(arg);
    else if (!h[0] || h[0] === "main" || h[0] === "toc") { viewHome(); if (h[0]) setTimeout(() => (document.getElementById(h[0]) || {}).scrollIntoView && document.getElementById(h[0]).scrollIntoView(), 30); }
    else notFound();
    if (h[0] !== "main" && h[0] !== "toc") window.scrollTo(0, 0);
    $app.focus({ preventScroll: true });
  }
  window.addEventListener("hashchange", route);
  load().then(route).catch(() => { $app.innerHTML = '<p class="bk-loading">Книга пока не открылась. Попробуйте обновить страницу или откройте <a href="../guides/">путеводители</a>.</p>'; });
})();
