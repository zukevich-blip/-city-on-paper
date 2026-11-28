/* The gallery: free exploration of every work the museum may show (Benoist sheets, the Heidelberg album, exhibitions,
 * open-access views by other masters). Routes: #/gallery #/art/<id> #/table #/guess #/showcase. Rights come from the
 * museums' own statements (see tools/world/build_gallery.py); nothing is shown without a source link. */
(function () {
  const B = (window.CoPBook = window.CoPBook || {});
  B.routes = B.routes || {};
  let G = null;
  const load = () => G || (G = fetch("gallery.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }).then((d) => { d.works.forEach((w, i) => { w.idx = i; w.y = (String(w.d || "").match(/\b(1[5-9]\d\d)\b/) || [])[1] | 0; }); d.by = new Map(d.works.map((w) => [w.id, w])); return d; }));
  const E = (s) => B.esc(s);
  const SET = { benoist: "Листы Бенуа", album: "Альбом 1861", exhibit: "Выставки", open: "Открытые собрания" };
  const KINDS = { interior: "Интерьеры", panorama: "Панорамы", ruins: "Руины и античность", church: "Храмы", palace: "Дворцы", bridge: "Мосты", square: "Площади и улицы" };
  const era = (y) => (y ? (y < 1700 ? "XVII и раньше" : y < 1800 ? "XVIII век" : y < 1850 ? "1800–1849" : "1850 и позже") : null);
  const ruTitle = (w) => (w.set === "benoist" || w.set === "album") ? w.t : `${w.kr || "Вид"}${w.c ? ", " + w.c : ""}`;
  const state = { q: "", c: "", k: "", set: "", a: "", e: "", mode: "mosaic", take: 72, lens: "all" };
  let lastList = [];
  const filt = (g) => g.works.filter((w) => (!state.set || w.set === state.set) && (!state.c || w.c === state.c) && (!state.k || w.k === state.k) && (!state.a || w.a === state.a) && (!state.e || era(w.y) === state.e)
    && (!state.q || (w.t + " " + w.to + " " + w.a + " " + (w.c || "") + " " + (w.kr || "") + " " + (w.m || "")).toLowerCase().includes(state.q.toLowerCase())));
  const count = (list, key) => { const m = new Map(); list.forEach((w) => { const v = typeof key === "function" ? key(w) : w[key]; if (v) m.set(v, (m.get(v) || 0) + 1); }); return [...m].sort((a, b) => b[1] - a[1]); };
  const rnd = (n) => Math.floor(Math.random() * n);
  const seeded = (seed) => () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const daySeed = () => { const d = new Date(); return (d.getFullYear() * 400 + d.getMonth() * 31 + d.getDate()) % 2147483646 + 1; };
  const tbl = () => { try { return JSON.parse(localStorage.getItem("cop-table") || "[]"); } catch (e) { return []; } };
  const saveTbl = (a) => { try { localStorage.setItem("cop-table", JSON.stringify(a.slice(0, 6))); } catch (e) { /* private mode */ } };
  const tile = (w) => `<a class="gt" href="#/art/${E(w.id)}" data-id="${E(w.id)}"><img src="${E(w.th)}" alt="${E(ruTitle(w))}" loading="lazy" width="${Math.round(w.w >= w.h ? 360 : 360 * w.w / w.h)}" height="${Math.round(w.w >= w.h ? 360 * w.h / w.w : 360)}"><span class="gcap"><b>${E(B.cut(ruTitle(w), 40))}</b><span>${E(B.cut(w.a, 34))}${w.y ? " · " + w.y : ""}</span></span></a>`;
  const chip = (key, val, label, n, on) => `<button type="button" class="gchip" data-k="${key}" data-v="${E(val)}" aria-pressed="${on}">${E(label)}${n ? ` <i>${n}</i>` : ""}</button>`;

  const LENSES = [["all", "Всё", {}], ["cities", "Города", { c: "*" }], ["masters", "Мастера", { a: "*" }], ["eras", "Эпохи", { e: "*" }], ["interior", "Интерьеры", { k: "interior" }], ["panorama", "Панорамы", { k: "panorama" }], ["ruins", "Античность", { k: "ruins" }], ["benoist", "Бенуа", { set: "benoist" }]];

  async function viewGallery() {
    B.setTitle("Галерея"); B.crumbs([{ t: "Книга", href: "#/" }, { t: "Галерея" }]);
    let g; try { g = await load(); } catch (e) { return B.notFound(); }
    const all = g.works, list = filt(g); lastList = list;
    const lensRow = LENSES.map(([id, t, p]) => `<button type="button" class="glens" data-lens="${id}" aria-pressed="${state.lens === id}">${t}</button>`).join("");
    const facet = state.lens === "masters" ? ["a", count(all, "a").slice(0, 24)] : state.lens === "eras" ? ["e", count(all, (w) => era(w.y))] : state.lens === "cities" || state.lens === "all" ? ["c", count(all, "c").filter(([c, n]) => n >= 10 || state.c === c).slice(0, 12)] : ["k", count(all, "kr").map(([t, n]) => [Object.keys(KINDS).find((k) => KINDS[k] === t || (t === "Площадь и улица" && k === "square")) || t, n])];
    const facetChips = facet[1].map(([v, n]) => chip(facet[0], v, facet[0] === "k" ? (KINDS[v] || v) : v, n, state[facet[0]] === v)).join("");
    const setChips = ["benoist", "album", "exhibit", "open"].map((s) => chip("set", s, SET[s], all.filter((w) => w.set === s).length, state.set === s)).join("");
    const shown = list.slice(0, state.take);
    const body = state.mode === "folio"
      ? `<div class="folio">${shown.map((w, i) => `<a class="fpage" href="#/art/${E(w.id)}"><img src="${E(w.i)}" alt="${E(ruTitle(w))}" loading="lazy" width="${w.w}" height="${w.h}"><span class="fcap">${E(ruTitle(w))}<i>${E(w.a)}</i></span><span class="fnum">${i + 1}</span></a>`).join("")}</div>`
      : `<div class="gmasonry">${shown.map(tile).join("")}</div>`;
    B.app().innerHTML = `<div class="page-enter gallery"><section class="chead compact"><p class="eyebrow">Свободное исследование</p><h1>Галерея</h1><p class="small" role="status">${B.plural(list.length, "работа", "работы", "работ")} из ${all.length}. Каждая открывается крупно, с музеем, правами и ссылкой на оригинал.</p></section>
      <div class="gtools"><input id="gq" type="search" placeholder="Поиск: город, мастер, сюжет" aria-label="Поиск по галерее" value="${E(state.q)}"><div class="gbtns"><button type="button" class="btn ghost" id="grand">Случайный шедевр</button><a class="btn ghost" href="#/table">Световой стол${tbl().length ? " · " + tbl().length : ""}</a><a class="btn ghost" href="#/guess">Угадай город</a><a class="btn ghost" href="#/showcase">Показ на весь экран</a></div></div>
      <div class="glenses" role="group" aria-label="Кураторские линзы">${lensRow}</div>
      <div class="gchips" role="group" aria-label="Уточнить">${facetChips}</div>
      <div class="gchips" role="group" aria-label="Собрание">${setChips}${chip("mode", state.mode === "folio" ? "mosaic" : "folio", state.mode === "folio" ? "Мозаика" : "Развороты in-folio", 0, false)}${(state.q || state.c || state.k || state.set || state.a || state.e) ? `<button type="button" class="gchip" id="greset">Сбросить</button>` : ""}</div>
      ${list.length ? body : `<div class="nolook"><b>Ничего не найдено.</b> Попробуйте другое слово или сбросьте фильтры.</div>`}
      ${list.length > state.take ? `<p class="btn-row"><button type="button" class="btn ghost wide" id="gmore">Показать ещё ${Math.min(72, list.length - state.take)}</button></p>` : ""}
      ${B.dock({ href: "#/exhibitions", t: "Выставки" }, { href: "#/", t: "Оглавление" })}</div>`;
    const re = () => viewGallery();
    document.getElementById("gq").addEventListener("change", (e) => { state.q = e.target.value.trim(); state.take = 72; re(); });
    document.querySelectorAll(".gchip[data-k]").forEach((b) => b.addEventListener("click", () => { const k = b.dataset.k, v = b.dataset.v; if (k === "mode") state.mode = v; else state[k] = state[k] === v ? "" : v; state.take = 72; re(); }));
    document.querySelectorAll(".glens").forEach((b) => b.addEventListener("click", () => { const id = b.dataset.lens, p = LENSES.find((l) => l[0] === id)[2]; Object.assign(state, { q: "", c: "", k: "", set: "", a: "", e: "", take: 72, lens: id }); for (const [k, v] of Object.entries(p)) if (v !== "*") state[k] = v; re(); }));
    const rs = document.getElementById("greset"); if (rs) rs.addEventListener("click", () => { Object.assign(state, { q: "", c: "", k: "", set: "", a: "", e: "", take: 72, lens: "all" }); re(); });
    const more = document.getElementById("gmore"); if (more) { more.addEventListener("click", () => { state.take += 72; re(); }); }
    document.getElementById("grand").addEventListener("click", () => { const pool = list.length ? list : all; location.hash = "#/art/" + pool[rnd(pool.length)].id; });
  }

  const related = (g, w) => {
    const pick = (f, n) => g.works.filter((x) => x.id !== w.id && f(x)).sort((a, b) => Math.abs(a.y - w.y) - Math.abs(b.y - w.y)).slice(0, n);
    return [["Тот же мастер", pick((x) => x.a === w.a && w.set !== "album", 10)], [`${w.c || "Тот же город"}: другие виды`, w.c ? pick((x) => x.c === w.c && x.a !== w.a, 10) : []], [`${w.kr || "Тот же сюжет"}`, w.k ? pick((x) => x.k === w.k && x.c !== w.c, 10) : []]].filter(([, l]) => l.length);
  };
  async function viewArt(id) {
    let g; try { g = await load(); } catch (e) { return B.notFound(); }
    const w = g.by.get(id); if (!w) return B.notFound();
    B.setTitle(ruTitle(w)); B.crumbs([{ t: "Книга", href: "#/" }, { t: "Галерея", href: "#/gallery" }, { t: B.cut(ruTitle(w), 28) }]);
    const list = lastList.length && lastList.includes(w) ? lastList : g.works, i = list.indexOf(w), nx = list[i + 1], pv = list[i - 1];
    const onTable = tbl().includes(w.id), pano = w.k === "panorama" && w.w / w.h >= 1.8;
    B.app().innerHTML = `<div class="page-enter plate artpage" data-art="${E(w.id)}"><section class="chead compact"><p class="eyebrow">${E(SET[w.set])}${w.c ? " · " + E(w.c) : ""}${w.kr ? " · " + E(w.kr) : ""}</p><h1>${E(ruTitle(w))}</h1><p class="small">${E(w.a)}${w.d ? " · " + E(w.d) : ""}</p>${w.to && w.to !== ruTitle(w) ? `<p class="small orig">Название в музее: <i>${E(B.cut(w.to, 140))}</i></p>` : ""}</section>
      <figure class="lt-sheet artfig" id="artfig"><div class="zoomwrap${pano ? " pano" : ""}" id="zoomwrap" tabindex="0" aria-label="${pano ? "Панорама: прокручивайте вбок" : "Работа крупно"}"><img id="zoomimg" src="${E(w.i)}" alt="${E(ruTitle(w))}" width="${w.w}" height="${w.h}"></div>
        <figcaption class="lt-imprint"><span class="l">${E(w.m)}</span><span class="c">${E(w.r)}</span><span class="r">${E(w.n)}</span></figcaption></figure>
      <div class="lt-tool artctl"><button type="button" class="btn ghost" id="artFull">Во весь экран</button><button type="button" class="btn ghost" id="artTable">${onTable ? "Убрать со стола" : "На световой стол"}</button><button type="button" class="btn ghost" id="artRand">Случайный шедевр</button>${w.link ? `<a class="btn" href="${E(w.link)}">Страница в книге →</a>` : ""}</div>
      <details class="lt-tool" id="deepBox"><summary>Смотреть вблизи</summary><p class="small">Файл не меняется; приближение щипком, двойным касанием или колесом.</p><div id="deepHost" class="deephost"></div></details>
      <details class="lt-tool" id="cabBox"><summary>Кабинет деталей: девять фрагментов</summary><div id="cabinet" class="cabinet"></div><div id="cabBig" class="cabbig" hidden></div><p class="small">Фрагменты вырезаны автоматически, подписей деталей пока нет; нажмите фрагмент, чтобы увеличить.</p></details>
      <dl class="facts"><dt>Название</dt><dd>${E(w.to)}</dd><dt>Автор</dt><dd>${E(w.a)}</dd><dt>Дата</dt><dd>${E(w.d || "в записи не указана")}</dd><dt>Музей</dt><dd>${E(w.m)}, ${E(w.n)}</dd><dt>Права</dt><dd>${E(w.r)}</dd><dt>Оригинал</dt><dd><a href="${E(B.safe(w.u))}" target="_blank" rel="noopener">запись в музее ↗</a></dd></dl>
      ${related(g, w).map(([t, l]) => `<h2>${E(t)}</h2><div class="rail" role="list">${l.map((x) => `<a role="listitem" class="gt rt" href="#/art/${E(x.id)}"><img src="${E(x.th)}" alt="${E(ruTitle(x))}" loading="lazy" width="150" height="${Math.round(150 * x.h / x.w)}"><span class="gcap"><b>${E(B.cut(ruTitle(x), 30))}</b></span></a>`).join("")}</div>`).join("")}
      ${B.dock(nx ? { href: "#/art/" + nx.id, t: B.cut(ruTitle(nx), 24), small: "Дальше" } : { href: "#/gallery", t: "В галерею" }, pv ? { href: "#/art/" + pv.id, t: B.cut(ruTitle(pv), 20) } : { href: "#/gallery", t: "Галерея" })}</div>`;
    const fig = document.getElementById("artfig");
    document.getElementById("artFull").addEventListener("click", () => { fig.classList.toggle("fs"); if (fig.requestFullscreen && fig.classList.contains("fs")) fig.requestFullscreen().catch(() => {}); else if (document.fullscreenElement) document.exitFullscreen(); });
    fig.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement) fig.classList.remove("fs"); });
    document.getElementById("artTable").addEventListener("click", (e) => { let t = tbl(); if (t.includes(w.id)) t = t.filter((x) => x !== w.id); else { t.push(w.id); if (t.length > 6) t = t.slice(-6); } saveTbl(t); e.target.textContent = t.includes(w.id) ? "Убрать со стола" : "На световой стол"; });
    document.getElementById("artRand").addEventListener("click", () => { location.hash = "#/art/" + g.works[rnd(g.works.length)].id; });
    document.getElementById("deepBox").addEventListener("toggle", async (e) => {
      const host = document.getElementById("deepHost"); if (!e.target.open || host.dataset.on) return; host.dataset.on = "1";
      try { const OSD = await B.loadOsd(); host.classList.add("deep"); window.__osd = OSD({ element: host, showNavigationControl: false, drawer: "canvas", placeholderFillStyle: "#eae3d1", visibilityRatio: 1, maxZoomPixelRatio: 3, tileSources: { type: "image", url: w.i } }); }
      catch (err) { host.textContent = "Просмотр вблизи сейчас недоступен."; }
    });
    document.getElementById("cabBox").addEventListener("toggle", (e) => { if (e.target.open) cabinet(w); });
  }
  function cabinet(w) {
    const host = document.getElementById("cabinet"); if (host.dataset.on) return; host.dataset.on = "1";
    const im = new Image(); im.onload = () => {
      const N = 3, cw = im.naturalWidth / N, ch = im.naturalHeight / N;
      for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) {
        const cv = document.createElement("canvas"); cv.width = 200; cv.height = Math.round(200 * ch / cw); cv.getContext("2d").drawImage(im, c * cw, r * ch, cw, ch, 0, 0, cv.width, cv.height);
        const b = document.createElement("button"); b.type = "button"; b.className = "cabtile"; b.setAttribute("aria-label", `Фрагмент ${r * N + c + 1}`); b.append(cv);
        b.addEventListener("click", () => { const big = document.getElementById("cabBig"), bc = document.createElement("canvas"); const k = 2.4; bc.width = Math.min(900, cw * 1.0 * 2.4 | 0); bc.height = Math.round(bc.width * ch / cw); bc.getContext("2d").drawImage(im, c * cw, r * ch, cw, ch, 0, 0, bc.width, bc.height); big.innerHTML = ""; big.append(bc); big.hidden = false; big.scrollIntoView({ block: "nearest" }); });
        host.append(b);
      }
    }; im.onerror = () => { host.textContent = "Фрагменты сейчас недоступны."; }; im.src = w.i;
  }

  async function viewTable() {
    B.setTitle("Световой стол"); B.crumbs([{ t: "Книга", href: "#/" }, { t: "Галерея", href: "#/gallery" }, { t: "Световой стол" }]);
    let g; try { g = await load(); } catch (e) { return B.notFound(); }
    let ids = tbl().filter((x) => g.by.has(x)), light = "day", layout = "grid";
    const draw = () => {
      const ws = ids.map((x) => g.by.get(x));
      B.app().innerHTML = `<div class="page-enter"><section class="chead compact"><p class="eyebrow">Куратору</p><h1>Световой стол</h1><p class="small">Положите до шести работ рядом, смените освещение и сравните. Работы показываются как есть, без наложения и подгонки.</p></section>
        <div class="lt-tool" role="group" aria-label="Освещение">${[["day", "Дневной свет"], ["lamp", "Лампа"], ["night", "Ночь"]].map(([k, t]) => `<button type="button" class="btn ghost lightb" data-l="${k}" aria-pressed="${light === k}">${t}</button>`).join("")}${ws.length >= 2 ? `<button type="button" class="btn ghost" id="tLayout">${layout === "grid" ? "Шторка: две первые" : "Показать сеткой"}</button>` : ""}<button type="button" class="btn ghost" id="tRand">Положить шесть случайных</button>${ws.length ? `<button type="button" class="btn ghost" id="tClear">Очистить</button>` : ""}</div>
        <div class="board ${light}" id="board">${!ws.length ? `<p class="boardempty">Стол пуст. Откройте работу в галерее и нажмите «На световой стол» или положите шесть случайных.</p>` : layout === "curtain" ? `<div class="curtain" id="curtain"><img class="cA" src="${E(ws[0].i)}" alt="${E(ruTitle(ws[0]))}"><div class="cB"><img src="${E(ws[1].i)}" alt="${E(ruTitle(ws[1]))}"></div><input type="range" id="cRange" min="0" max="100" value="50" aria-label="Шторка между двумя работами"></div><p class="small boardcap">${E(ruTitle(ws[0]))} (слева) и ${E(ruTitle(ws[1]))} (справа): два отдельных кадра, перспективы не совмещаются.</p>` : `<div class="boardgrid">${ws.map((w) => `<figure class="bfig"><a href="#/art/${E(w.id)}"><img src="${E(w.i)}" alt="${E(ruTitle(w))}" loading="lazy"></a><figcaption>${E(B.cut(ruTitle(w), 40))}<i>${E(w.a)}</i><button type="button" class="tdel" data-id="${E(w.id)}" aria-label="Убрать со стола">✕</button></figcaption></figure>`).join("")}</div>`}</div>
        ${B.dock({ href: "#/gallery", t: "Галерея" }, { href: "#/", t: "Оглавление" })}</div>`;
      document.querySelectorAll(".lightb").forEach((b) => b.addEventListener("click", () => { light = b.dataset.l; draw(); }));
      const lay = document.getElementById("tLayout"); if (lay) lay.addEventListener("click", () => { layout = layout === "grid" ? "curtain" : "grid"; draw(); });
      document.getElementById("tRand").addEventListener("click", () => { ids = []; while (ids.length < 6) { const w = g.works[rnd(g.works.length)]; if (!ids.includes(w.id)) ids.push(w.id); } saveTbl(ids); draw(); });
      const cl = document.getElementById("tClear"); if (cl) cl.addEventListener("click", () => { ids = []; saveTbl(ids); draw(); });
      document.querySelectorAll(".tdel").forEach((b) => b.addEventListener("click", () => { ids = ids.filter((x) => x !== b.dataset.id); saveTbl(ids); draw(); }));
      const rg = document.getElementById("cRange"); if (rg) rg.addEventListener("input", () => { document.querySelector(".cB").style.clipPath = `inset(0 0 0 ${rg.value}%)`; }), rg && (document.querySelector(".cB").style.clipPath = "inset(0 0 0 50%)");
    };
    draw();
  }

  async function viewGuess() {
    B.setTitle("Угадай город"); B.crumbs([{ t: "Книга", href: "#/" }, { t: "Галерея", href: "#/gallery" }, { t: "Угадай город" }]);
    let g; try { g = await load(); } catch (e) { return B.notFound(); }
    const cities = count(g.works.filter((w) => w.c && w.set !== "album"), "c").filter(([, n]) => n >= 8).map(([c]) => c);
    const pool = g.works.filter((w) => w.c && cities.includes(w.c) && w.set !== "album");
    let score = 0, round = 0;
    const next = () => {
      const w = pool[rnd(pool.length)], opts = [w.c]; while (opts.length < Math.min(4, cities.length)) { const c = cities[rnd(cities.length)]; if (!opts.includes(c)) opts.push(c); }
      opts.sort(() => Math.random() - 0.5); round++;
      B.app().innerHTML = `<div class="page-enter guess"><section class="chead compact"><p class="eyebrow">Игра · раунд ${round} · очки ${score}</p><h1>Угадай город по детали</h1></section><div class="guesscv"><canvas id="gcv" width="360" height="360" role="img" aria-label="Фрагмент гравюры"></canvas></div><div class="gopts" role="group" aria-label="Варианты">${opts.map((c) => `<button type="button" class="btn ghost gopt">${E(c)}</button>`).join("")}</div><p id="gres" class="small" role="status"></p><p class="btn-row"><button type="button" class="btn" id="gnext" hidden>Дальше →</button><a class="btn ghost" id="gwork" href="#/art/${E(w.id)}" hidden>Открыть работу</a></p>${B.dock({ href: "#/gallery", t: "Галерея" }, { href: "#/", t: "Оглавление" })}</div>`;
      const im = new Image(); im.onload = () => { const s = Math.min(im.naturalWidth, im.naturalHeight) * 0.32, x = Math.random() * (im.naturalWidth - s), y = Math.random() * (im.naturalHeight - s); document.getElementById("gcv").getContext("2d").drawImage(im, x, y, s, s, 0, 0, 360, 360); }; im.src = w.i;
      document.querySelectorAll(".gopt").forEach((b) => b.addEventListener("click", () => { const ok = b.textContent === w.c; if (ok) score++; document.querySelectorAll(".gopt").forEach((x) => { x.disabled = true; if (x.textContent === w.c) x.setAttribute("aria-pressed", "true"); }); document.getElementById("gres").textContent = ok ? `Верно: ${w.c}. «${ruTitle(w)}», ${w.a}.` : `Это ${w.c}: «${ruTitle(w)}», ${w.a}.`; document.getElementById("gnext").hidden = false; document.getElementById("gwork").hidden = false; }));
      document.getElementById("gnext").addEventListener("click", next);
    };
    next();
  }

  let showTimer = null;
  async function viewShowcase() {
    let g; try { g = await load(); } catch (e) { return B.notFound(); }
    const rr = seeded(daySeed()), pick = g.works.filter((w) => w.w >= 700 && w.h >= 500).sort(() => rr() - 0.5).slice(0, 40); let i = 0, play = true;
    document.body.classList.add("showmode");
    B.app().innerHTML = `<div class="showcase" id="show"><img id="showImg" alt=""><div class="showcap" id="showCap"></div><button type="button" class="showx" id="showX" aria-label="Выйти из показа">✕</button></div>`;
    const show = () => { const w = pick[(i + pick.length) % pick.length], im = document.getElementById("showImg"); im.style.opacity = 0; setTimeout(() => { im.src = w.i; im.alt = ruTitle(w); im.onload = () => { im.style.opacity = 1; }; document.getElementById("showCap").innerHTML = `<a href="#/art/${E(w.id)}">${E(ruTitle(w))}</a><span>${E(w.a)}${w.y ? " · " + w.y : ""} · ${E(w.m)}</span>`; }, 250); };
    const stop = () => { clearInterval(showTimer); document.body.classList.remove("showmode"); document.removeEventListener("keydown", key); if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); };
    const key = (e) => { if (e.key === "Escape") { stop(); location.hash = "#/gallery"; } else if (e.key === "ArrowRight") { i++; show(); } else if (e.key === "ArrowLeft") { i--; show(); } else if (e.key === " ") { play = !play; e.preventDefault(); } };
    document.addEventListener("keydown", key); showTimer = setInterval(() => { if (play) { i++; show(); } }, 7000); show();
    document.getElementById("showX").addEventListener("click", () => { stop(); location.hash = "#/gallery"; });
    const el = document.getElementById("show"); if (el.requestFullscreen) el.requestFullscreen().catch(() => {});
    window.addEventListener("hashchange", () => { if (!/^#\/showcase/.test(location.hash)) stop(); }, { once: true });
  }

  /* home: a mosaic of different works instead of one repeated lithograph; no text over the pictures */
  B.mountHome = async function (host) {
    let g; try { g = await load(); } catch (e) { host.innerHTML = ""; return; }
    const rr = seeded(daySeed()), mix = (f, n) => g.works.filter(f).sort(() => rr() - 0.5).slice(0, n);
    const hero = mix((w) => w.w >= 900 && w.k && w.set !== "album", 5), mosaic = [...mix((w) => w.c === "Рим", 3), ...mix((w) => w.c === "Венеция", 3), ...mix((w) => w.c === "Париж" && w.set !== "album", 3), ...mix((w) => w.k === "interior", 2), ...mix((w) => w.set === "benoist", 3), ...mix((w) => w.k === "panorama", 2)];
    const cities = count(g.works, "c").slice(0, 6);
    host.innerHTML = `<div class="homehero" id="hh">${hero.map((w, i) => `<a class="hslide${i ? "" : " on"}" href="#/art/${E(w.id)}"><img src="${E(w.i)}" alt="${E(ruTitle(w))}"${i ? ' loading="lazy"' : ""}><span class="hcap"><b>${E(ruTitle(w))}</b><i>${E(w.a)}${w.y ? " · " + w.y : ""}</i></span></a>`).join("")}</div>
      <nav class="hdoors" aria-label="Входы в музей"><a class="hdoor" href="#/gallery"><b>${g.count}</b><span>работ в галерее</span></a><a class="hdoor" href="#/exhibitions"><b>3</b><span>выставки</span></a><a class="hdoor" href="#/albums"><b>71</b><span>планша альбома 1861</span></a><a class="hdoor" href="#/benoist"><b>102</b><span>листа Бенуа</span></a><a class="hdoor" href="#/table"><b>◐</b><span>световой стол</span></a><a class="hdoor" href="#/guess"><b>?</b><span>угадай город</span></a></nav>
      <div class="gmasonry home">${mosaic.map(tile).join("")}</div>
      <p class="btn-row"><button type="button" class="btn" id="hRand">Случайный шедевр</button><a class="btn ghost" href="#/showcase">Показ на весь экран</a><a class="btn ghost" href="#/gallery">Вся галерея</a></p>
      <div class="gchips" role="group" aria-label="Города">${cities.map(([c, n]) => `<a class="gchip" href="#/gallery" data-city="${E(c)}">${E(c)} <i>${n}</i></a>`).join("")}</div>`;
    host.querySelectorAll("[data-city]").forEach((a) => a.addEventListener("click", () => { Object.assign(state, { q: "", c: a.dataset.city, k: "", set: "", a: "", e: "", take: 72, lens: "cities" }); }));
    document.getElementById("hRand").addEventListener("click", () => { location.hash = "#/art/" + g.works[rnd(g.works.length)].id; });
    const slides = [...host.querySelectorAll(".hslide")]; let k = 0;
    if (slides.length > 1) setInterval(() => { if (!document.body.contains(host)) return; slides[k].classList.remove("on"); k = (k + 1) % slides.length; slides[k].classList.add("on"); }, 6000);
  };

  Object.assign(B.routes, { gallery: viewGallery, art: viewArt, table: viewTable, guess: viewGuess, showcase: viewShowcase });
})();
