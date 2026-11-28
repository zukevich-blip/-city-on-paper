/* "Внутри истории": building dossiers from real materials. Order: facade -> door -> interior -> plan -> section -> today.
 * Nothing is reconstructed: a missing interior, plan or section is stated. The door journey is a montage of two real pictures. */
(function () {
  const B = (window.CoPBook = window.CoPBook || { routes: {} });
  B.routes = B.routes || {};
  const E = (s) => B.esc(s);
  let X = null;
  const load = () => X || (X = fetch("inside.json").then((r) => r.json()));
  const ruTitle = (w) => (w.set === "benoist" || w.set === "album" ? w.t : `${w.kr || "Вид"}${w.c ? ", " + w.c : ""}`);
  const card = (w) => `<a class="gt rt" href="#/art/${E(w.id)}"><img src="${E(w.th)}" alt="${E(ruTitle(w))}" loading="lazy" width="150" height="${Math.round(150 * w.h / w.w)}"><span class="gcap"><b>${E(B.cut(ruTitle(w), 34))}</b><span>${E(B.cut(String(w.a).split(";")[0].replace(/\s*\(.*$/, ""), 28))}${w.y ? " · " + w.y : ""}</span></span></a>`;
  const credit = (x) => `<figcaption class="excap"><b>${E(x.caption)}</b><span class="small">${E(x.credit)} · ${E(x.licence)}${x.page && /^https:\/\/(?!api\.panoramax\.xyz\/api\/collections\/$)/.test(x.page) ? ` · <a href="${E(x.page)}" target="_blank" rel="noopener">источник ↗</a>` : ""}</span></figcaption>`;
  const fig = (x, cls = "") => `<figure class="exfig insfig ${cls}"><img src="${E(x.i)}" alt="${E(x.caption)}" loading="lazy">${credit(x)}</figure>`;

  async function viewList() {
    B.setTitle("Внутри истории"); B.crumbs([{ t: "Книга", href: "#/" }, { t: "Внутри истории" }]);
    let d, g; try { [d, g] = await Promise.all([load(), B.loadGallery()]); } catch (e) { return B.notFound(); }
    const cover = (b) => { const w = g.by.get(b.facade[0]); return w ? w.i : (b.extras[0] || b.plan[0] || {}).i; };
    B.app().innerHTML = `<div class="page-enter"><section class="chead compact"><p class="eyebrow">Здания изнутри</p><h1>Внутри истории</h1><p class="lede">От фасада на литографии к двери, интерьеру, плану, разрезу и сегодняшнему состоянию. Только подлинные материалы: чего нет, то названо.</p></section>
      <div class="exlist">${d.buildings.map((b) => `<a class="exhall" href="#/inside/${E(b.id)}"><img src="${E(cover(b))}" alt="" loading="lazy"><span class="cap"><span class="where">${E(b.city)} · ${[b.interior.length + b.extras.length ? "интерьер" : "", b.plan.length ? "план" : "", b.section.length ? "разрез" : "", b.modern.length ? "сегодня" : ""].filter(Boolean).join(" · ") || "фасад"}</span><b>${E(b.title)}</b><span class="hook">${E(B.cut(b.lede, 130))}</span></span></a>`).join("")}</div>
      <h2>Истории</h2><div class="exlist" id="storyList"></div>
      ${B.dock({ href: "#/halls", t: "Залы" }, { href: "#/", t: "Оглавление" })}</div>`;
    try { const S = await loadStories(); document.getElementById("storyList").innerHTML = S.stories.map((x) => { const f = (x.scenes && x.scenes[0] && x.scenes[0].work) || (x.turns && x.turns[0].work) || (x.pieces && x.pieces[0].work); const w = g.by.get(f); return `<a class="exhall" href="#/story/${E(x.id)}"><img src="${E(w ? w.i : "")}" alt="" loading="lazy"><span class="cap"><span class="where">${E(x.city)} · ${{ scenes: "сцены", dialogue: "диалог", biography: "биография здания" }[x.layout]}</span><b>${E(x.title)}</b><span class="hook">${E(B.cut(x.lede, 120))}</span></span></a>`; }).join(""); } catch (e) { /* stories are optional */ }
  }

  function journey(b) {
    const j = b.journey; if (!j) return "";
    const A = b.modern[j.from], C = b.modern[j.to];
    return `<section class="insec" id="door"><h2>Через дверной проём</h2><div class="door" id="doorStage" style="--dx:${j.door[0]}%;--dy:${j.door[1]}%"><img class="dA" src="${E(A.i)}" alt="${E(A.caption)}"><img class="dB" src="${E(C.i)}" alt="${E(C.caption)}"><div class="dmark" aria-hidden="true"></div></div>
      <div class="lt-tool"><label for="doorT"><span class="lt-legend">Подойти к двери и войти</span></label><input id="doorT" type="range" min="0" max="100" value="0"><button type="button" class="btn ghost" id="doorPlay">▶ Войти</button></div><p class="small">${E(j.note)} ${E(A.credit)}; ${E(C.credit)}.</p></section>`;
  }
  const wireDoor = () => {
    const st = document.getElementById("doorStage"); if (!st) return; const r = document.getElementById("doorT"), A = st.querySelector(".dA"), C = st.querySelector(".dB");
    const set = (t) => { const k = t / 100, e = k * k * (3 - 2 * k), zoom = 1 + 7 * Math.min(1, k / 0.62), fadeA = Math.max(0, 1 - Math.max(0, (k - 0.5) / 0.25)), fadeB = Math.max(0, Math.min(1, (k - 0.55) / 0.3));
      A.style.transform = `scale(${zoom})`; A.style.opacity = fadeA; C.style.opacity = fadeB; C.style.transform = `scale(${1.35 - 0.35 * e})`; st.dataset.t = t; };
    r.addEventListener("input", () => set(Number(r.value))); set(0);
    let raf = null; document.getElementById("doorPlay").addEventListener("click", (e) => { if (raf) { cancelAnimationFrame(raf); raf = null; e.target.textContent = "▶ Войти"; return; }
      if (matchMedia("(prefers-reduced-motion: reduce)").matches) { r.value = r.value > 50 ? 0 : 100; set(Number(r.value)); return; }
      const from = Number(r.value) >= 100 ? 0 : Number(r.value), t0 = performance.now(); e.target.textContent = "❚❚ Пауза";
      const step = (n) => { const v = Math.min(100, from + ((n - t0) / 5000) * 100); r.value = v; set(v); if (v < 100) raf = requestAnimationFrame(step); else { raf = null; e.target.textContent = "↺ Ещё раз"; } }; raf = requestAnimationFrame(step); });
  };

  async function viewBuilding(id) {
    let d, g; try { [d, g] = await Promise.all([load(), B.loadGallery()]); } catch (e) { return B.notFound(); }
    const b = d.buildings.find((x) => x.id === id); if (!b) return B.notFound();
    B.setTitle(b.title); B.crumbs([{ t: "Книга", href: "#/" }, { t: "Внутри истории", href: "#/inside" }, { t: b.title }]);
    const W = (ids) => ids.map((i) => g.by.get(i)).filter(Boolean);
    const facade = W(b.facade), inter = W(b.interior);
    const stages = [["facade", "Фасад", facade.length], ["door", "Дверь", b.journey ? 1 : 0], ["interior", "Внутри", inter.length + b.extras.length], ["plan", "План", b.plan.length], ["section", "Разрез", b.section.length], ["today", "Сегодня", b.modern.length]];
    const idx = d.buildings.indexOf(b), nx = d.buildings[idx + 1], pv = d.buildings[idx - 1];
    B.app().innerHTML = `<div class="page-enter inside"><section class="chead compact"><p class="eyebrow">${E(b.city)} · внутри истории</p><h1>${E(b.title)}</h1><p class="lede">${E(b.lede)}</p>
        <nav class="stagenav" aria-label="Этапы">${stages.map(([k, t, n]) => `<a class="gchip${n ? "" : " off"}" href="#${k === "today" ? "today" : k}" data-go="${k}" aria-disabled="${!n}">${t}${n ? ` <i>${n}</i>` : " <i>нет</i>"}</a>`).join("")}</nav></section>
      <section class="insec" id="facade"><h2>Фасад на листах и гравюрах</h2>${facade.length ? `<div class="rail" role="list">${facade.map(card).join("")}</div>` : '<p class="small">Листов фасада в фонде нет.</p>'}</section>
      ${journey(b)}
      <section class="insec" id="interior"><h2>Внутри</h2>${inter.length || b.extras.length ? `<div class="rail" role="list">${inter.map(card).join("")}</div><div class="insgrid">${b.extras.map((x) => fig(x)).join("")}</div>` : '<p class="small">Подлинного интерьера этого здания в фонде нет, поэтому дверь не открывается: мы не подставляем чужие залы.</p>'}</section>
      <section class="insec" id="plan"><h2>План</h2>${b.plan.length ? `<div class="insgrid">${b.plan.map((x) => fig(x, "plan")).join("")}</div>` : '<p class="small">Плана в открытых собраниях пока не найдено.</p>'}</section>
      <section class="insec" id="section"><h2>Разрез: что держит своды и купола</h2>${b.section.length ? `<div class="insgrid">${b.section.map((x) => fig(x, "plan")).join("")}</div><p class="small">Это подлинный чертёж-источник; его подпись выше. Мы не дорисовываем конструкции.</p>` : '<p class="small">Разреза в открытых собраниях не найдено.</p>'}</section>
      <section class="insec" id="today"><h2>Сегодня</h2>${b.modern.length ? `<div class="insgrid">${b.modern.map((x) => fig(x)).join("")}</div>` : '<p class="small">Современного снимка в фонде пока нет.</p>'}</section>
      <section class="insec"><h2>Чего не хватает</h2><ul class="facts-list unk">${b.missing.map((t) => `<li>${E(t)}</li>`).join("")}</ul>${b.place ? `<p class="btn-row"><a class="btn ghost" href="#/place/${E(b.place)}">История места в книге →</a></p>` : ""}</section>
      ${B.dock(nx ? { href: "#/inside/" + nx.id, t: nx.title, small: "Следующее здание" } : { href: "#/inside", t: "Все здания" }, pv ? { href: "#/inside/" + pv.id, t: pv.title } : { href: "#/inside", t: "Здания" })}</div>`;
    wireDoor();
    document.querySelectorAll("[data-go]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); const t = document.getElementById(a.dataset.go === "today" ? "today" : a.dataset.go); if (t && t.scrollIntoView) t.scrollIntoView({ behavior: "smooth", block: "start" }); }));
  }

  /* three illustrated stories, three compositions */
  let ST = null;
  const loadStories = () => ST || (ST = fetch("stories.json").then((r) => r.json()));
  const resolve = (it, g, d) => {
    if (it.work) { const w = g.by.get(it.work); return w && { i: w.i, th: w.th, w: w.w, h: w.h, title: ruTitle(w), sub: `${String(w.a).split(";")[0].replace(/\s*\(.*$/, "")}${w.d ? " · " + w.d : ""}`, credit: `${w.m} · ${w.r}`, link: "#/art/" + w.id }; }
    const b = d.buildings.find((x) => x.id === (it.extra || it.modern || {}).building); if (!b) return null;
    if (it.extra) { const pool = b.extras.concat(b.plan, b.section).filter((x) => !it.extra.kind || x.kind === it.extra.kind), x = pool[it.extra.n || 0]; return x && { i: x.i, title: x.caption, sub: x.credit, credit: x.licence, link: null }; }
    const m = b.modern[it.modern.n || 0]; return m && { i: m.i, title: m.caption, sub: m.credit, credit: m.licence, link: null };
  };
  const plate = (x, cls = "") => x ? `<figure class="exfig insfig ${cls}">${x.link ? `<a class="eximg" href="${E(x.link)}">` : '<div class="eximg">'}<img src="${E(x.i)}" alt="${E(x.title)}" loading="lazy">${x.link ? "</a>" : "</div>"}<figcaption class="excap"><b>${E(x.title)}</b><span>${E(x.sub)}</span><span class="small">${E(x.credit)}</span></figcaption></figure>` : "";
  async function viewStory(id) {
    let S, g, d; try { [S, g, d] = await Promise.all([loadStories(), B.loadGallery(), load()]); } catch (e) { return B.notFound(); }
    const st = S.stories.find((x) => x.id === id); if (!st) return B.notFound();
    B.setTitle(st.title); B.crumbs([{ t: "Книга", href: "#/" }, { t: "Внутри истории", href: "#/inside" }, { t: st.title }]);
    let body = "";
    if (st.layout === "scenes") body = st.scenes.map((s, n) => { const x = resolve(s, g, d); return x ? `<section class="scene" style="--n:${n}"><p class="eyebrow">${E(s.kicker)}</p>${plate(x, "sceneimg")}</section>` : ""; }).join("");
    else if (st.layout === "dialogue") body = `<div class="dialog">${st.turns.map((t) => { const x = resolve(t, g, d); return x ? `<div class="turn ${t.side}">${plate(x)}</div>` : ""; }).join("")}</div>`;
    else body = `<ol class="bio">${st.events.map((e, n) => `<li class="bioev"><span class="when">${E(e.date)}</span><p>${E(e.text)}</p><a class="src" href="${E(B.safe(e.source))}" target="_blank" rel="noopener">${E(e.source_name)} ↗</a>${st.pieces.filter((p) => p.after === n).map((p) => `<div class="piece">${plate(resolve(p, g, d))}<p class="small">${E(p.label)}</p></div>`).join("")}</li>`).join("")}</ol>`;
    const idx = S.stories.indexOf(st), nx = S.stories[idx + 1], pv = S.stories[idx - 1];
    B.app().innerHTML = `<div class="page-enter story story-${E(st.layout)}"><section class="chead compact"><p class="eyebrow">${E(st.city)} · история</p><h1>${E(st.title)}</h1><p class="lede">${E(st.lede)}</p></section>${body}<p class="small closing">${E(st.closing)}</p>${B.dock(nx ? { href: "#/story/" + nx.id, t: nx.title, small: "Следующая история" } : { href: "#/inside", t: "Здания" }, pv ? { href: "#/story/" + pv.id, t: pv.title } : { href: "#/inside", t: "Здания" })}</div>`;
  }
  Object.assign(B.routes, { inside: (arg) => (arg ? viewBuilding(arg) : viewList()), story: viewStory });
})();
