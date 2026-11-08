/* City on Paper — optional design experiment. Real atlas data and real map.
 * Album pages are editorial navigation, not invented artifacts or substituted scans.
 */
"use strict";
(() => {
  const $ = selector => document.querySelector(selector);
  const add = (tag, cls, content) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (content !== undefined) node.textContent = content;
    return node;
  };
  const safe = value => typeof value === "string" && /^https:\/\//i.test(value) ? value : "";
  const deep = city => "../eras/#/city/" + encodeURIComponent(city.id);
  const featured = ["paris", "florence", "rim", "naples", "venetsiya", "london"];
  let A, bookCity = null, bookPage = 0;
  function setMode(mode) {
    const m = mode === "book" ? "book" : "desk";
    document.body.dataset.mode = m;
    document.querySelectorAll("[data-mode]").forEach(btn => {
      if (btn.tagName === "BUTTON") btn.setAttribute("aria-pressed", String(btn.dataset.mode === m));
    });
    const url = new URL(location.href);
    if (m === "book") url.searchParams.set("view", "book");
    else url.searchParams.delete("view");
    history.replaceState(null, "", url.href);
    setTimeout(() => { if (window.__deskMap) window.__deskMap.invalidateSize(); }, 100);
  }
  document.querySelectorAll(".mode-toggle button").forEach(btn =>
    btn.addEventListener("click", () => setMode(btn.dataset.mode)));

  const dialog = $("#folioDialog"), left = $("#folioLeft"), right = $("#folioRight"),
    pageLabel = $("#folioPage"), spread = $("#folioSpread");
  function paragraph(parent, value) { parent.append(add("p", "", value)); }
  function anchor(parent, text, href, external) {
    const a = add("a", "", text); a.href = href;
    if (external) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
    parent.append(a); return a;
  }
  function workOf(city) {
    const all = (city.works || []).filter(w => w && w.image && /^https:\/\//.test(w.image) && safe(w.url));
    return all.find(w => w.rights_class === "open") || null;
  }
  function artwork(parent, city) {
    const w = workOf(city);
    if (!w) {
      const n = add("div", "folio-art-fallback", "Архивные виды города");
      parent.append(n);
      paragraph(parent, "На демонстрационном развороте не подставляем изображения с непроверенными правами.");
      return;
    }
    const figure = add("figure");
    const image = add("img"); image.alt = w.title || "Литография города";
    image.loading = "lazy"; image.src = w.image; image.referrerPolicy = "no-referrer";
    image.addEventListener("error", () => {
      const fallback = add("div", "folio-art-fallback", "Изображение в архиве");
      image.replaceWith(fallback);
    });
    const cap = add("figcaption", "", [w.artist || "Автор уточняется", w.title || "Без названия",
      w.institution || "Коллекция", w.date || ""].filter(Boolean).join(" · "));
    figure.append(image, cap); parent.append(figure);
    anchor(parent, "Открыть оригинальную карточку у хранителя", safe(w.url), true);
  }
  function rebuild() {
    if (!bookCity) return;
    spread.classList.remove("turning"); left.replaceChildren(); right.replaceChildren();
    pageLabel.textContent = String(bookPage + 1) + " / 3";
    $("#folioPrev").disabled = bookPage === 0;
    $("#folioNext").disabled = bookPage === 2;
    const city = bookCity;
    left.append(add("small", "", "ГОРОДСКОЕ СОБРАНИЕ · ТОМ I"));
    right.append(add("small", "", "АТЛАС ЭПОХ · ПОДЛИННЫЕ ИСТОЧНИКИ"));
    if (bookPage === 0) {
      left.append(add("h2", "", city.name));
      paragraph(left, city.country + (city.area ? " · " + city.area : ""));
      paragraph(left, "Начните с карты, затем перейдите к музейным работам и сравнениям разных лет. Архив хранит отдельные записи и ракурсы, их нельзя автоматически считать точным совпадением.");
      left.append(add("div", "folio-number", "I"));
      right.append(add("h2", "", "Первый лист"));
      artwork(right,city);
    } else if (bookPage === 1) {
      left.append(add("h2", "", "Художники и листы"));
      const works = city.works || [];
      if (works.length) {
        paragraph(left, "В географическом каталоге отмечено " + works.length + " работ Бенуа. Дополнительные авторы и исторические виды доступны в полном городском собрании.");
        for (const w of works.slice(0, 4)) {
          const p = add("p", "", [w.date || "Дата уточняется", w.title || "Без названия"].join(" · "));
          left.append(p);
        }
      } else paragraph(left, "Работы других авторов и музейные каталоги проверяются отдельно. Не все изображения доступны для публичного показа.");
      left.append(add("div", "folio-number", "II"));
      right.append(add("h2", "", "Читать оригинал"));
      artwork(right,city);
    } else {
      left.append(add("h2", "", "Город во времени"));
      paragraph(left, "В цифровом музее сохранены историческая и современная карты. Там, где материалов достаточно, есть несколько эпох, увеличение листов и добавление личной фотографии без её публикации.");
      paragraph(left, "Для научного исследования используйте музейные первоисточники, датировки и подписи авторов.");
      left.append(add("div", "folio-number", "III"));
      right.append(add("h2", "", "Продолжить прогулку"));
      const old = add("div", "folio-art-fallback", city.name + " · " + city.country);
      right.append(old);
      anchor(right, "Открыть город, карты и все изображения", deep(city), false);
      paragraph(right, "На следующем экране находятся настоящие музейные материалы и действующие ползунки сравнения.");
    }
  }
  function openBook(city) {
    bookCity = city; bookPage = 0; rebuild();
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.open = true;
  }
  $("#folioClose").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", e => { if (e.target === dialog) dialog.close(); });
  function turn(step) {
    const next = Math.max(0, Math.min(2, bookPage + step));
    if (next === bookPage) return;
    bookPage = next;
    rebuild();
    if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
      void spread.offsetHeight; spread.classList.add("turning");
    }
  }
  $("#folioNext").addEventListener("click", () => turn(1));
  $("#folioPrev").addEventListener("click", () => turn(-1));
  dialog.addEventListener("keydown", e => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault(); turn(e.key === "ArrowRight" ? 1 : -1);
    }
  });
  function createAlbums() {
    const host = $("#albumStack"); host.replaceChildren();
    const choices = featured.map(id => A.cities.find(c=>c.id === id)).filter(Boolean);
    for (const [index, city] of choices.entries()) {
      const button = add("button", "album-book"); button.type = "button";
      button.dataset.city = city.id;
      button.setAttribute("aria-label", "Открыть альбом города " + city.name);
      button.append(add("span", "", ["I", "II", "III", "IV", "V", "VI"][index]));
      const body = add("div");
      body.append(add("strong", "", city.name),
        add("small", "", city.country + " · " + (city.works || []).length + " листов Бенуа в географическом каталоге"));
      button.append(body); button.addEventListener("click", () => openBook(city));
      host.append(button);
    }
  }
  function searchCities() {
    const q = $("#citySearch").value.trim().toLocaleLowerCase("ru");
    const results = $("#suggestions"); results.replaceChildren();
    if (!q) return;
    const hits = A.cities.filter(c =>
      [c.name,c.name_orig,c.country,c.area].some(v => String(v || "").toLocaleLowerCase("ru").includes(q))).slice(0, 9);
    for (const city of hits) {
      const row = add("a"); row.href = deep(city);
      row.append(add("span", "", city.name), add("small", "", city.country)); results.append(row);
    }
    if (!hits.length) results.append(add("p", "", "Город не найден. Откройте полный атлас."));
  }
  $("#citySearch").addEventListener("input", searchCities);
  async function initialize() {
    const host = $("#deskMap");
    try {
      const response = await fetch("../eras/data/atlas.json", {cache:"default"});
      if (!response.ok) throw Error("Каталог: " + response.status);
      A = await response.json();
      createAlbums();
      if (!window.Maps || !window.L) throw Error("Библиотека карт не загрузилась");
      const atlas = {...A,portal:{...A.portal,tiles:{...A.portal.tiles,
        tiles:"../eras/" + A.portal.tiles.tiles}}};
      host.replaceChildren();
      window.__deskMap = Maps.portal(host, atlas, null);
      if (window.__deskMap) requestAnimationFrame(() => window.__deskMap.invalidateSize());
    } catch (error) {
      host.replaceChildren();
      const p=add("p", "", "Карта недоступна в этом просмотре. Основной атлас работает отдельно.");
      const a=add("a", "", "Перейти в основной атлас");
      a.href="../eras/";
      host.append(p,a);
      console.error("City on Paper desk preview: ",error.message);
    }
  }
  addEventListener("hashchange", () => {
    const matched = /^#\/city\/([a-z0-9_\-]+)$/.exec(location.hash);
    if (matched) location.replace("../eras/#/city/" + matched[1]);
  });
  setMode(new URLSearchParams(location.search).get("view") === "book" ? "book" : "desk");
  initialize();
})();