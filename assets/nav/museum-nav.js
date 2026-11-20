/* Город на бумаге — единая навигация по всем залам музея (одна строка сверху на каждой странице).
 * Подключение: <script src="<путь>/assets/nav/museum-nav.js" defer></script>. Ссылки строятся от адреса самого скрипта. */
(() => {
  "use strict";
  const me = document.currentScript || [...document.scripts].find((s) => /assets\/nav\/museum-nav\.js/.test(s.src));
  if (!me || document.getElementById("museumBar")) return;
  const base = me.src.replace(/assets\/nav\/museum-nav\.js.*$/, "");
  const HALLS = [
    ["Главный вход", [["", "Живой музей", "Истории, коллекция, мастерская и все разделы"], ["book/", "Книга видов", "Оглавление по странам и городам: листайте по порядку"], ["guides/", "Путеводители", "Оцифрованные книги, альбомы и связанные городские виды"], ["walk/", "Маршрут по времени", "Карта, исторические листы и современный вид в одном путешествии"], ["stories/", "Истории", "Документированные рассказы по произведениям и городам"], ["atlas/", "Научный атлас · исследования", "Каталог мест, источников и географических доказательств"], ["experience/", "Книга городов", "Необязательное путешествие с раскрывающейся книгой"], ["eras/", "Карты и сравнение эпох", "Интерактивные карты, разные годы, шторка и свои изображения"]]],
    ["Смотреть", [["salon/", "Салон открытий", "Литографии и картины из открытых музеев"], ["closeup/", "Кабинет деталей", "Рассматривать лист в подробностях"],
      ["exhibitions/city-as-evidence/", "Город как свидетельство", "Выставка: что рассказывает гравюра"], ["exhibitions/lost-florence/", "Исчезнувшая Флоренция", "Выставка о старом центре"],
      ["photography/", "Современный город", "Фотографии тех же мест сегодня"]]],
    ["Путешествовать", [["journeys/", "Путешествие по векам", "Города по векам"], ["cities/", "Все города мира", "Географический каталог с источниками и степенью проверки"], ["world/", "Мировая галерея", "Отобранные открытые произведения за пределами Европы"],
      ["poc/compare/", "Тогда / сейчас", "Сравнить литографию и фотографию"], ["atlas-prototype/", "Первая карта · архив проекта", "Ранний экспериментальный вариант карты, не основной атлас"]]],
    ["Расследовать", [["discover/", "Первое расследование", "Начать знакомство"], ["detective/", "Дело № 01 · Мадлен", "Литография под лупой"],
      ["fieldwork/", "Городская фотоохота", "Найти ракурс художника самому"], ["submit/", "Предложить находку", "Представить свою литографию, фотографию или исторический материал"], ["studio/", "Кабинет коллекционера", "Происхождение листов, блокнот"]]],
    ["Как это сделано", [["printlab/", "Камень и бумага", "Как печатали литографию"], ["atelier/bargue/", "Школа рисунка", "Учиться рисовать по-старому"],
      ["ornaments/", "Мастерская орнамента", "Узоры и декор"], ["ideas/", "Лаборатория идей", "Куда растёт музей"]]],
  ];
  const here = location.pathname.replace(/index\.html$/, "");
  // The curated homepage owns its primary navigation. Keep the global bar in inner rooms.
  if (here === new URL(base).pathname) return;
  const isHere = (p) => {
    if (p.includes("#")) { const [path, hash] = p.split("#"); return here.endsWith("/" + path) && location.hash.startsWith("#" + hash); }
    if (p === "eras/" && /^#\/epoch/.test(location.hash)) return false;
    return here.endsWith("/" + p) || (p === "" && new URL(base).pathname === here);
  };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const css = `#museumBar{background:#29463D;color:#f4efe5;font:13px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;position:sticky;top:0;z-index:1000;border-bottom:1px solid #bfae97}
#museumBar .mb{max-width:1500px;margin:0 auto;display:flex;align-items:center;gap:6px 12px;padding:4px clamp(12px,3vw,40px);flex-wrap:wrap}
#museumBar .mbback{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 10px;
 border:1px solid #dcb88c8a;border-radius:3px;white-space:nowrap;text-decoration:none;font:12px/1.4 system-ui}
#museumBar .mbback:hover{background:#ffffff1a}
#museumBar a{color:#eadfc9;text-decoration:none}#museumBar .mbh{font:15px "Iowan Old Style",Georgia,serif;letter-spacing:.02em;margin-right:auto;display:inline-flex;align-items:center;min-height:44px}
#museumBar .mbq{display:flex;gap:2px;flex-wrap:wrap}#museumBar .mbq a{display:inline-flex;align-items:center;min-height:44px;padding:0 8px;border-radius:2px}#museumBar .mbq a:hover,#museumBar .mbq a[aria-current]{background:#ffffff1a}
#museumBar button{min-height:44px;border:1px solid #dcb88c;background:none;color:#f1e3c4;padding:4px 12px;border-radius:2px;font:inherit;cursor:pointer}
#museumBar .mbp[hidden]{display:none!important}
#museumBar a:focus-visible,#museumBar button:focus-visible{outline:3px solid #b79567;outline-offset:2px}
#museumBar .mbp{position:absolute;left:0;right:0;top:100%;max-width:1500px;margin:0 auto;padding:12px clamp(12px,3vw,40px) 20px;display:grid;
 max-height:min(76dvh,720px);overflow-y:auto;background:#29463D;box-shadow:0 18px 33px #07150c99;
 border-bottom:1px solid #bfae97;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px 22px;overscroll-behavior:contain}
#museumBar .mbp .mbt{font:600 11px system-ui;letter-spacing:.16em;text-transform:uppercase;color:#c9a96e;margin:8px 0 4px}
#museumBar .mbp a{display:block;min-height:44px;padding:7px 0;border-bottom:1px solid #ffffff14}#museumBar .mbp a b{font:400 16px Georgia,serif;display:block}#museumBar .mbp a small{color:#b8ad98}
#museumBar .mbp a[aria-current] b{color:#f0c987}
@media(max-width:700px){
 #museumBar{position:relative}
 #museumBar .mb{flex-wrap:nowrap;gap:7px}
 #museumBar .mbh{font-size:14px;min-width:0;overflow:hidden;text-overflow:ellipsis}
 #museumBar .mbback{padding:0 9px;font-size:12px}
 #museumBar .mb{flex-wrap:wrap!important;padding-bottom:0}
 #museumBar .mbq{order:9;flex:1 0 100%;display:flex;flex-wrap:nowrap;overflow-x:auto;gap:0;margin:0 -4px;scrollbar-width:none;border-top:1px solid #ffffff1f}
 #museumBar .mbq::-webkit-scrollbar{display:none}
 #museumBar .mbq a{flex:none;padding:0 10px;font-size:13px}
 #museumBar .mbp{max-height:75dvh;grid-template-columns:1fr!important;padding:8px 16px 18px}
 #museumBar .mbp a{min-height:44px}
 #museumBar button{padding:4px 9px;white-space:nowrap}
/* Mobile: keep one compact toolbar; all sections remain available from the menu. */
#museumBar .mb{flex-wrap:nowrap!important;padding:4px 12px;min-height:52px;gap:7px}
#museumBar .mbq{display:none!important}
#museumBar .mbh{min-width:0;flex:1 1 auto;font-size:14px}
#museumBar .mbback{flex:0 0 auto;min-height:44px;border-radius:9px}
#museumBar button{flex:0 0 auto;min-height:44px;border-radius:9px}
#museumBar .mbp{top:100%;max-height:min(70dvh,640px);overflow-y:auto;overscroll-behavior:contain}
}`;
  const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
  // One primary menu for the whole museum — the same five doors as on the home page.
  const quick = [["book/", "Книга"], ["guides/", "Путеводители"], ["stories/", "Истории"], ["cities/", "Города"], ["eras/", "Атлас"], ["eras/#/epochs", "Эпохи"], ["salon/", "Каталог"]];
  const bar = document.createElement("div");
  bar.id = "museumBar";
  bar.innerHTML = `<div class="mb"><a class="mbh" href="${esc(base)}">Город на бумаге</a>
    <nav class="mbq" aria-label="Залы музея">${quick.map(([p, t]) => `<a href="${esc(base + p)}"${isHere(p) ? ' aria-current="page"' : ""}>${esc(t)}</a>`).join("")}</nav>
    <a class="mbback" href="${esc(base)}" id="museumBack" aria-label="Назад по музею или на главную">← Назад</a>
    <button type="button" aria-label="Открыть все залы музея" aria-expanded="false" aria-controls="museumPanel">Все залы ▾</button></div>
    <nav class="mbp" id="museumPanel" aria-label="Все залы музея" hidden>${HALLS.map(([h, items]) => `<div><p class="mbt">${esc(h)}</p>${items.map(([p, t, d]) =>
      `<a href="${esc(base + p)}"${isHere(p) ? ' aria-current="page"' : ""}><b>${esc(t)}</b><small>${esc(d)}</small></a>`).join("")}</div>`).join("")}</nav>`;
  document.body.insertBefore(bar, document.body.firstChild);
  // One header per page: a page-level header that only repeats the brand and section links is hidden
  // (headers that carry the page title or controls — h1, buttons, inputs — stay).
  for (const h of document.querySelectorAll("body > header, body > div > header")) {
    if (h.closest("#museumBar") || h.querySelector("h1, button, input, select, details, form")) continue;
    if (/Город на бумаге/.test(h.textContent) && h.querySelectorAll("a").length <= 9 && h.textContent.trim().length < 260) h.hidden = true;
  }
  const btn = bar.querySelector('[aria-controls="museumPanel"]'), panel = bar.querySelector("#museumPanel");
  const back = bar.querySelector("#museumBack");
  const closeMenu = (restoreFocus = false) => {
    if (panel.hidden) return;
    panel.hidden = true; btn.setAttribute("aria-expanded", "false");
    btn.textContent = "Все залы ▾"; btn.setAttribute("aria-label", "Открыть все залы музея");
    if (restoreFocus) btn.focus();
  };
  btn.addEventListener("click", () => {
    if (!panel.hidden) return closeMenu();
    panel.hidden = false; btn.setAttribute("aria-expanded", "true");
    btn.textContent = "Закрыть ▴"; btn.setAttribute("aria-label", "Закрыть меню музея");
  });
  document.addEventListener("pointerdown", (e) => {
    if (!panel.hidden && !bar.contains(e.target)) closeMenu();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) { e.preventDefault(); closeMenu(true); }
  });
  back.addEventListener("click", (e) => {
    const prev = document.referrer;
    if (prev && prev.startsWith(base) && history.length > 1) {
      e.preventDefault(); history.back();
    }
  });
  window.MuseumHalls = HALLS;
})();
